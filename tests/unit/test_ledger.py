import pytest
import uuid
from app.models.core import User, Wallet
from app.models.ledger import LedgerEntry
from app.services.ledger import LedgerService

def test_ledger_math_integrity(session):
    """
    Verifies that the LedgerService correctly calculates the balance 
    by summing up all historical LedgerEntries for a wallet.
    """
    user_id = uuid.uuid4()
    user = User(id=user_id, email="math_test@example.com", full_name="Math Geek")
    session.add(user)
    
    wallet = Wallet(wallet_number="5555555555", balance=0, user_id=user_id)
    session.add(wallet)
    session.commit()

    entry_1 = LedgerEntry(
        wallet_id=wallet.id,
        amount=50000,
        transaction_id=uuid.uuid4() # Mock ID
    )
    
    entry_2 = LedgerEntry(
        wallet_id=wallet.id,
        amount=-10000,
        transaction_id=uuid.uuid4()
    )
    
    entry_3 = LedgerEntry(
        wallet_id=wallet.id,
        amount=-50,
        transaction_id=uuid.uuid4()
    )
    
    entry_4 = LedgerEntry(
        wallet_id=wallet.id,
        amount=10000,
        transaction_id=uuid.uuid4()
    )

    session.add(entry_1)
    session.add(entry_2)
    session.add(entry_3)
    session.add(entry_4)
    session.commit()

    expected_balance = 49950
    
    ledger_service = LedgerService()
    
    calculated_balance = ledger_service.get_current_balance(session, wallet.id)

    assert calculated_balance == expected_balance, \
        f"Math failure! Expected {expected_balance}, got {calculated_balance}"