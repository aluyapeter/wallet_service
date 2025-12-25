import hmac
import hashlib
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, Request, Header, Query
from sqlmodel import Session, select, desc

from app.database import get_session
from app.models import User, Wallet, Transaction, TransactionType, TransactionStatus
from app.security import require_permission, verify_pin
from app.services.paystack import PaystackService
from app.config import settings
from app.schemas import DepositRequest, TransferRequest, WithdrawalRequest
import logging
from app.limiter import limiter
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wallet", tags=["Wallet"])

@router.post("/deposit")
@limiter.limit("10/minute")
async def initiate_deposit(
    request: Request,
    request_data: DepositRequest,
    user: User = Depends(require_permission("deposit")),
    session: Session = Depends(get_session)
):
    """
    Initiates a deposit via Paystack.
    """
    if request_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    reference = str(uuid.uuid4())

    paystack = PaystackService()

    try:
        paystack_data = await paystack.initialize_transaction(
            email=user.email,
            amount=request_data.amount,
            reference=reference
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment initialization failed: {str(e)}")

    if not user.wallet:
        raise HTTPException(status_code=400, detail="User does not have a wallet linked")

    new_txn = Transaction(
        amount=request_data.amount,
        transaction_type=TransactionType.DEPOSIT,
        status=TransactionStatus.PENDING,
        reference=reference,
        wallet_id=user.wallet.id,
        meta_data=paystack_data
    )
    
    session.add(new_txn)
    session.commit()
    session.refresh(new_txn)

    return {
        "authorization_url": paystack_data["authorization_url"],
        "reference": reference,
        # "data" : paystack_data
    }


@router.post("/paystack/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(None),
    session: Session = Depends(get_session)
):
    """
    Handles updates from Paystack. Verified via HMAC signature.
    """
    if not x_paystack_signature:
        raise HTTPException(status_code=400, detail="Missing signature header")
    
    payload_bytes = await request.body()
    
    expected_signature = hmac.new(
        key=settings.PAYSTACK_SECRET_KEY.encode(),
        msg=payload_bytes,
        digestmod=hashlib.sha512
    ).hexdigest()


    if not hmac.compare_digest(expected_signature, x_paystack_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        event_data = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event_data.get("event")

    if event_type != "charge.success":
        return {"status": "ignored", "message": "Event type not monitored"}

    data = event_data.get("data", {})
    reference = data.get("reference")
    amount_paid = data.get("amount") 
    statement = select(Transaction).where(Transaction.reference == reference)
    transaction = session.exec(statement).first()

    if not transaction:
        return {"status": "error", "message": "Transaction not found"}

    if transaction.status == TransactionStatus.SUCCESS:
        return {"status": "ignored", "message": "Transaction already processed"}

    try:
        wallet_stmt = (
            select(Wallet)
            .where(Wallet.id == transaction.wallet_id)
            .with_for_update()
        )
        wallet = session.exec(wallet_stmt).first()

        if not wallet:
            return {"status": "error", "message": "Wallet not found"}

        wallet.balance += amount_paid
        transaction.status = TransactionStatus.SUCCESS

        session.add(transaction)
        session.add(wallet)
        session.commit()
        
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": "Internal server error"}

    return {"status": "success"}

@router.post("/transfer")
@limiter.limit("20/minute")
def transfer_funds(
    request: Request,
    request_data: TransferRequest,
    user: User = Depends(require_permission("transfer")),
    session: Session = Depends(get_session)
):
    """
    Internal wallet-to-wallet transfer.
    """
    if user.pin_hash is None:
        raise HTTPException(status_code=400, detail="Transaction PIN not set")
    
    pin = verify_pin(request_data.pin, user.pin_hash)
    if not pin:
        raise HTTPException(status_code=400, detail="Invalid Transaction PIN.")
    
    if request_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    sender_wallet = user.wallet
    if not sender_wallet:
        raise HTTPException(status_code=400, detail="You do not have a wallet")

    if sender_wallet.balance < request_data.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    statement = select(Wallet).where(Wallet.wallet_number == request_data.wallet_number)
    receiver_wallet = session.exec(statement).first()

    if not receiver_wallet:
        raise HTTPException(status_code=404, detail="Recipient wallet not found")

    if sender_wallet.id == receiver_wallet.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to yourself")

    reference = str(uuid.uuid4())

    sender_wallet.balance -= request_data.amount
    receiver_wallet.balance += request_data.amount

    sender_txn = Transaction(
        amount=-request_data.amount,
        transaction_type=TransactionType.TRANSFER,
        status=TransactionStatus.SUCCESS,
        reference=reference,
        wallet_id=sender_wallet.id,
        meta_data={"direction": "sent", "recipient": receiver_wallet.wallet_number}
    )

    receiver_txn = Transaction(
        amount=request_data.amount,
        transaction_type=TransactionType.TRANSFER,
        status=TransactionStatus.SUCCESS,
        reference=f"{reference}-credit",
        wallet_id=receiver_wallet.id,
        meta_data={"direction": "received", "sender": sender_wallet.wallet_number}
    )

    session.add(sender_wallet)
    session.add(receiver_wallet)
    session.add(sender_txn)
    session.add(receiver_txn)
    
    session.commit()
    
    return {"status": "success", "message": "Transfer successful", "reference": reference}

@router.get("/balance")
@limiter.limit("100/minute")
def get_balance(
    request: Request,
    user: User = Depends(require_permission("read"))
):
    """
    Returns the current wallet balance.
    """
    if not user.wallet:
        raise HTTPException(status_code=404, detail="No wallet found")
    
    return {
        "balance": user.wallet.balance,
        "currency": user.wallet.currency
    }

@router.get("/transactions")
@limiter.limit("50/minute")
def get_transactions(
    request: Request,
    user: User = Depends(require_permission("read")),
    session: Session = Depends(get_session),
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Max records to return")
):
    """
    Returns the list of all transactions for the user's wallet.
    """
    if not user.wallet:
        raise HTTPException(status_code=404, detail="No wallet found")

    statement = (
        select(Transaction)
        .where(Transaction.wallet_id == user.wallet.id)
        .order_by(desc(Transaction.created_at))
        .offset(skip)
        .limit(limit)
    )
    transactions = session.exec(statement).all()
    
    return transactions


@router.get("/deposit/{reference}/status")
async def get_deposit_status(
    reference: str,
    user: User = Depends(require_permission("read")),
    session: Session = Depends(get_session)
):
    """
    Checks the status of a specific deposit.
    
    Compliance Update: 
    - If Paystack says "failed/reversed", we update DB to FAILED (allowed).
    - If Paystack says "success", we DO NOT update DB/credit wallet (strictly compliant).
    """
    statement = select(Transaction).where(Transaction.reference == reference)
    txn = session.exec(statement).first()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if not user.wallet or txn.wallet_id != user.wallet.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this transaction")

    if txn.status == TransactionStatus.PENDING:
        paystack = PaystackService()

        try:
            verification_data = await paystack.verify_transaction(reference)
            gateway_status = verification_data.get("status") 

            if gateway_status in ["failed", "reversed", "abandoned"]:
                txn.status = TransactionStatus.FAILED
                session.add(txn)
                session.commit()
                session.refresh(txn)
            
            elif gateway_status == "success":
                 return {
                    "reference": txn.reference,
                    "status": "success",
                    "amount": txn.amount,
                    "note": "Payment confirmed. Wallet will be credited shortly via webhook."
                }

        except Exception as e:
            print(f"Verification error: {e}")

    return {
        "reference": txn.reference,
        "status": txn.status,
        "amount": txn.amount
    }

@router.post("/withdraw")
async def withdraw_funds(
    request: WithdrawalRequest,
    user: User = Depends(require_permission("transfer")),
    session: Session = Depends(get_session)
):
    if not user.pin_hash:
        raise HTTPException(400, "PIN not set")
    if not verify_pin(request.pin, user.pin_hash):
        raise HTTPException(401, "Invalid PIN")

    wallet = user.wallet
    if not wallet:
        raise HTTPException(status_code=400, detail="User does not have a linked wallet")
    if wallet.balance < request.amount:
        raise HTTPException(400, "Insufficient funds")

    original_balance = wallet.balance
    wallet.balance -= request.amount
    session.add(wallet)
    session.commit()
    session.refresh(wallet)

    paystack = PaystackService()
    
    recipient_code = await paystack.create_transfer_recipient(
        name=request.account_name,
        account_number=request.account_number,
        bank_code=request.bank_code
    )
    
    if not recipient_code:
        wallet.balance += request.amount
        session.add(wallet)
        session.commit()
        raise HTTPException(500, "Failed to register bank account with provider")

    reference = f"wth-{uuid.uuid4()}"
    transfer_result = await paystack.initiate_transfer(
        amount=request.amount,
        recipient_code=recipient_code,
        reference=reference,
        reason="Wallet Withdrawal"
    )

    if not transfer_result["status"]:
        wallet.balance += request.amount
        session.add(wallet)
        session.commit()
        logger.error(f"Withdrawal failed for {user.email}: {transfer_result['message']}")
        raise HTTPException(502, "Transfer failed at provider")

    txn = Transaction(
        amount=-request.amount,
        transaction_type=TransactionType.WITHDRAWAL,
        status=TransactionStatus.PENDING,
        reference=reference,
        wallet_id=wallet.id,
        meta_data={"bank": request.bank_code, "account": request.account_number}
    )
    session.add(txn)
    session.commit()

    return {"status": "success", "message": "Withdrawal processing", "reference": reference}