import pytest
from app.models.core import User, Wallet
from app.security import create_access_token

def test_pin_security_lifecycle(client, session, test_user):
    token = create_access_token(subject=test_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    recipient = User(email="recipient@test.com", full_name="Recipient")
    session.add(recipient)
    session.commit()
    
    recipient_wallet = Wallet(
        wallet_number="0987654321", 
        balance=0, 
        user_id=recipient.id
    )
    session.add(recipient_wallet)
    session.commit()

    payload = {
        "wallet_number": "0987654321",
        "amount": 1000,
        "pin": "1234"
    }
    response = client.post("/wallet/transfer", json=payload, headers=headers)
    
    assert response.status_code == 400
    assert "Transaction PIN not set" in response.json()["detail"]

    pin_payload = {"pin": "1234"}
    response = client.post("/auth/set-pin", json=pin_payload, headers=headers)
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    session.refresh(test_user)
    assert test_user.pin_hash is not None

    response = client.post("/auth/set-pin", json={"pin": "9999"}, headers=headers)
    
    assert response.status_code == 400
    assert "PIN already set" in response.json()["detail"]

    payload["pin"] = "0000"
    response = client.post("/wallet/transfer", json=payload, headers=headers)
    
    assert response.status_code == 400 
    assert "Invalid Transaction PIN" in response.json()["detail"]

    payload["pin"] = "1234"
    response = client.post("/wallet/transfer", json=payload, headers=headers)
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    session.refresh(test_user.wallet)
    session.refresh(recipient_wallet)
    
    assert test_user.wallet.balance == 49000
    assert recipient_wallet.balance == 1000