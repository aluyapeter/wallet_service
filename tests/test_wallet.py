from app.security import create_access_token

def test_get_balance(client, test_user):
    token = create_access_token(subject=test_user.id)
    
    response = client.get(
        "/wallet/balance",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == 50000
    assert data["currency"] == "NGN"

def test_transfer_funds_success(client, session, test_user):
    from app.models import User, Wallet
    recipient = User(email="recipient@example.com", full_name="Recipient")
    session.add(recipient)
    session.commit()
    rec_wallet = Wallet(wallet_number="0987654321", balance=0, user_id=recipient.id)
    session.add(rec_wallet)
    session.commit()
    
    token = create_access_token(subject=test_user.id)

    payload = {
        "wallet_number": "0987654321",
        "amount": 5000
    }
    response = client.post(
        "/wallet/transfer",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    
    session.refresh(test_user.wallet)
    session.refresh(rec_wallet)
    
    assert test_user.wallet.balance == 45000
    assert rec_wallet.balance == 5000

def test_transfer_insufficient_funds(client, test_user):
    token = create_access_token(subject=test_user.id)
    
    payload = {
        "wallet_number": "0000000000",
        "amount": 99999999
    }
    response = client.post(
        "/wallet/transfer",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 400
    assert "Insufficient funds" in response.json()["detail"]