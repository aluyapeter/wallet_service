import pytest
import asyncio
from unittest.mock import patch

async def test_withdrawal_reversal_on_failure(async_client, test_user):
    login_res = await async_client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword"
    })

    assert login_res.status_code == 200, f"Login failed: {login_res.text}"

    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    profile_response = await async_client.get("/auth/profile", headers=headers)
    assert profile_response.status_code == 200

    payload = {
        "amount": 50000,
        "pin": "1234",
        "bank_code": "057",
        "account_number": "1234567890",
        "account_name": "Test User"
    }


    # 1. Login & Get Token
    
    # 2. Check Initial Balance (Should be 50,000 from conftest)
    #    (You can verify this by hitting the /profile endpoint)

    # 3. Mock Paystack to FAIL
    #    Instead of returning success, make 'initiate_transfer' return:
    #    {"status": False, "message": "Bank downtime"}

    # 4. Attempt Withdrawal
    #    POST /wallet/withdraw with 10,000
    
    # 5. Assertions
    #    Check A: Response status code should be 502 (Bad Gateway)
    #    Check B: Hit /profile again. Balance should STILL be 50,000.