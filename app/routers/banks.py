from fastapi import APIRouter, HTTPException, Query, Depends
from app.services.paystack import PaystackService
from app.security import get_current_user
from app.models import User

router = APIRouter(tags=["Banks"])


@router.get("/banks")
async def list_banks():
    """
    Helpe endpoint to list banks and their codes
    """
    # service = PaystackService()
    banks = await PaystackService().get_banks()

    list = [
        {"name": bank["name"], "code": bank["code"]}
        for bank in banks
    ]
    return list

@router.get("/banks/resolve")
async def resolve_account_details(
    account_number: str = Query(..., min_length=10, max_length=10, description="NUBAN Account Number"),
    bank_code: str = Query(..., description="Bank code gotten from the bank list endpoint"),
    user: User = Depends(get_current_user)
):
    """
    Verifies an account number and returns the account name
    """
    service = PaystackService()
    account_data = await service.resolve_account(account_number, bank_code)

    if not account_data:
        raise HTTPException(status_code=404, detail="Could not resolve account, check number and bank")
    return {
        "account_name": account_data["account_name"],
        "account_number": account_data["account_number"],
        "bank_id": bank_code
    }