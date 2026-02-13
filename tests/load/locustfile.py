from locust import HttpUser, task, between, events
import random
import os

class WalletUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        """
        We need to login to get a Token. 
        We save the token to self.client.headers so all subsequent requests use it.
        """
        response = self.client.post("/auth/login", json={
            "email": "test_user@gmail.com", 
            "password": os.getenv("TEST_USER_PASSWORD")
        })

        if response.status_code == 200:
            token = response.json()["access_token"]
            self.client.headers.update({"Authorization": f"Bearer {token}"})
        else:
            print("Login failed! This user will die in jesus name.")
            self.stop()

    @task(6)
    def view_balance(self):
        with self.client.get("/wallet/balance", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Balance check failed: {response.text}")

    @task(1)
    def deposit_money(self):
        ref = f"locust-{random.randint(100000, 999999)}"
        payload = {
            "amount": 500000
        }
        
        self.client.post("/wallet/deposit", json=payload)

    @task(2)
    def transfer_money(self):
        payload = {
            "wallet_number": "0449316476",
            "amount": 100000,
            "description": "Load Test Transfer",
            "pin": "3009"
        }
        
        with self.client.post("/wallet/transfer", json=payload, catch_response=True) as response:
            if response.status_code == 400 and "Insufficient funds" in response.text:
                response.success()
            elif response.status_code != 200:
                response.failure(f"Transfer failed: {response.text}")

    @task(1)
    def view_transactions(self):
        self.client.get("/wallet/transactions?limit=10")