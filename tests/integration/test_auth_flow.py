from fastapi.testclient import TestClient

def test_full_auth_flow(client: TestClient, mock_email_service, mock_redis):
    
    user_data = {
        "email": "integration@test.com",
        "full_name": "Integration User",
        "password": "securepassword123",
        "confirm_password": "securepassword123"
    }
    
    response = client.post("/auth/signup", json=user_data)

    print(response.json())
    
    assert response.status_code == 200
    data = response.json()
    assert "wallet_number" in data
    assert data["email"] == "integration@test.com"
    
    verify_data = {
        "email": "integration@test.com",
        "otp": "000000" 
    }
    
    verify_response = client.post("/auth/verify-email", json=verify_data)
    assert verify_response.status_code == 200
    assert verify_response.json()["message"] == "Email verified successfully (Demo Mode)"

    login_data = {
        "email": "integration@test.com",
        "password": "securepassword123"
    }
    
    login_response = client.post("/auth/login", json=login_data)
    assert login_response.status_code == 200
    
    token = login_response.json()["access_token"]
    assert token is not None

    headers = {"Authorization": f"Bearer {token}"}
    profile_response = client.get("/auth/profile", headers=headers)
    assert profile_response.status_code == 200
    
    profile_data = profile_response.json()
    assert profile_data["email"] == "integration@test.com"
    assert profile_data["is_verified"] is True
    assert "wallet_number" in profile_data