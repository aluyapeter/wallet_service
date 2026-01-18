import pytest
import asyncio
from unittest.mock import patch

@pytest.mark.asyncio
async def test_double_spend(async_client, test_user, mock_redis, mock_email_service):
    login_res = await async_client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "amount": 50000,
        "pin": "1234",
        "bank_code": "057",
        "account_number": "1234567890",
        "account_name": "Test User"
    }

    with patch("app.services.paystack.PaystackService.create_transfer_recipient") as mock_recipient, \
         patch("app.services.paystack.PaystackService.initiate_transfer") as mock_transfer:
         
        mock_recipient.return_value = "RCP_fake_code"
        mock_transfer.return_value = {"status": True, "message": "Success"}

        task1 = async_client.post("/wallet/withdraw", json=payload, headers=headers)
        task2 = async_client.post("/wallet/withdraw", json=payload, headers=headers)
        
        responses = await asyncio.gather(task1, task2)

        success_count = sum(1 for r in responses if r.status_code == 200)
        failure_count = sum(1 for r in responses if r.status_code >= 400)

        assert success_count == 1, f"Double Spend Detected! Successes: {success_count}"
        assert failure_count == 1, f"Double Spend Detected! Failure: {failure_count}"