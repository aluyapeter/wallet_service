import hmac
import hashlib
import uuid
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlmodel import Session, select, desc

from app.database import get_session
from app.models import User, Wallet, Transaction, TransactionType, TransactionStatus
from app.security import require_permission
from app.services.paystack import paystack_client
from app.config import settings
from app.schemas import DepositRequest, TransferRequest

router = APIRouter(prefix="/wallet", tags=["Wallet"])

@router.post("/deposit")
async def initiate_deposit(
    request: DepositRequest,
    user: User = Depends(require_permission("deposit")),
    session: Session = Depends(get_session)
):
    """
    Initiates a deposit via Paystack.
    """
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    reference = str(uuid.uuid4())

    try:
        paystack_data = await paystack_client.initialize_transaction(
            email=user.email,
            amount=request.amount,
            reference=reference
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment initialization failed: {str(e)}")

    if not user.wallet:
        raise HTTPException(status_code=400, detail="User does not have a wallet linked")

    new_txn = Transaction(
        amount=request.amount,
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
        "status": "success",
        "message": "Transaction initialized",
        "authorization_url": paystack_data["authorization_url"],
        "reference": reference
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

    if event_data.get("event") != "charge.success":
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

    if transaction.amount != amount_paid:
         transaction.status = TransactionStatus.FAILED
         session.add(transaction)
         session.commit()
         return {"status": "error", "message": "Amount mismatch"}

    try:
        transaction.status = TransactionStatus.SUCCESS
        
        wallet = transaction.wallet
        wallet.balance += amount_paid
        
        session.add(transaction)
        session.add(wallet)
        session.commit()
        
    except Exception as e:
        session.rollback()
        print(f"Database Commit Error: {e}")
        return {"status": "error", "message": "Internal server error"}

    return {"status": "success"}

@router.post("/transfer")
def transfer_funds(
    request: TransferRequest,
    user: User = Depends(require_permission("transfer")),
    session: Session = Depends(get_session)
):
    """
    Internal wallet-to-wallet transfer.
    """
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    sender_wallet = user.wallet
    if not sender_wallet:
        raise HTTPException(status_code=400, detail="You do not have a wallet")

    if sender_wallet.balance < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    statement = select(Wallet).where(Wallet.wallet_number == request.wallet_number)
    receiver_wallet = session.exec(statement).first()

    if not receiver_wallet:
        raise HTTPException(status_code=404, detail="Recipient wallet not found")

    if sender_wallet.id == receiver_wallet.id:
        raise HTTPException(status_code=400, detail="Cannot transfer to yourself")

    reference = str(uuid.uuid4())

    sender_wallet.balance -= request.amount
    receiver_wallet.balance += request.amount

    sender_txn = Transaction(
        amount=-request.amount,
        transaction_type=TransactionType.TRANSFER,
        status=TransactionStatus.SUCCESS,
        reference=reference,
        wallet_id=sender_wallet.id,
        meta_data={"direction": "sent", "recipient": receiver_wallet.wallet_number}
    )

    receiver_txn = Transaction(
        amount=request.amount,
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
    
    return {"message": "Transfer successful", "reference": reference}

@router.get("/balance")
def get_balance(
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
def get_transactions(
    user: User = Depends(require_permission("read")),
    session: Session = Depends(get_session)
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
    )
    transactions = session.exec(statement).all()
    
    return transactions

@router.get("/deposit/{reference}/status")
def get_deposit_status(
    reference: str,
    user: User = Depends(require_permission("read")),
    session: Session = Depends(get_session)
):
    """
    Checks the status of a specific deposit reference.
    Only allows the owner of the wallet to check.
    """
    statement = select(Transaction).where(Transaction.reference == reference)
    txn = session.exec(statement).first()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if not user.wallet or txn.wallet_id != user.wallet.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this transaction")

    return {
        "reference": txn.reference,
        "transaction_status": txn.status,
        "amount": txn.amount,
        "created_at": txn.created_at
    }