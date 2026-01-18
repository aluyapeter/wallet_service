import pytest
from unittest.mock import patch
from app.models.core import User, Wallet
from app.security import create_access_token
import uuid

def test_pin_security_lifecycle(client, session):
    fresh_user_id = uuid.uuid4()
    fresh_user = User(
        id=fresh_user_id,
        email="fresh@test.com", 
        full_name="Fresh User",
        is_email_verified=True
    )
    session.add(fresh_user)
    
    fresh_wallet = Wallet(
        wallet_number="1112223333", 
        balance=5000000, 
        user=fresh_user 
    )
    session.add(fresh_wallet)
    session.commit()
    session.refresh(fresh_user)

    token = create_access_token(subject=fresh_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    recipient = User(email="recipient@test.com", full_name="Recipient")
    session.add(recipient)
    session.commit()
    recipient_wallet = Wallet(wallet_number="0987654321", balance=0, user_id=recipient.id)
    session.add(recipient_wallet)
    session.commit()

    payload = {
        "wallet_number": "0987654321",
        "amount": 1000,
        "pin": "0000"
    }
    client.post("/wallet/transfer", json=payload, headers=headers)
    client.post("/auth/set-pin", json={"pin": "1234"}, headers=headers)
    
    payload["pin"] = "0000"
    client.post("/wallet/transfer", json=payload, headers=headers)

    with patch("app.services.ledger.LedgerService.get_current_balance") as mock_balance:
        mock_balance.return_value = 5000000
        
        payload["pin"] = "1234"
        response = client.post("/wallet/transfer", json=payload, headers=headers)
    
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    session.refresh(fresh_wallet)
    assert fresh_wallet.balance == 4999000