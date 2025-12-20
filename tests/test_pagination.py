import pytest
from app.models import Transaction, TransactionType, TransactionStatus
from app.security import create_access_token

def test_pagination_flow(client, session, test_user):
    wallet = test_user.wallet
    
    for i in range(25):
        txn = Transaction(
            amount=100 + i,
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.SUCCESS,
            reference=f"ref-{i}",
            wallet_id=wallet.id,
            meta_data={"note": f"Transaction number {i}"}
        )
        session.add(txn)
    session.commit()

    token = create_access_token(subject=test_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/wallet/transactions?limit=10&skip=0", 
        headers=headers
    )
    data = response.json()
    
    assert response.status_code == 200
    assert len(data) == 10
    
    response = client.get(
        "/wallet/transactions?limit=10&skip=10", 
        headers=headers
    )
    data = response.json()
    assert len(data) == 10

    response = client.get(
        "/wallet/transactions?limit=10&skip=20", 
        headers=headers
    )
    data = response.json()
    assert len(data) == 5

    response = client.get(
        "/wallet/transactions?limit=10&skip=30", 
        headers=headers
    )
    data = response.json()
    assert len(data) == 0