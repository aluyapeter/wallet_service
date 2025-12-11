import httpx
from app.config import settings

PAYSTACK_BASE_URL = "https://api.paystack.co"

class PaystackService:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }

    async def initialize_transaction(self, email: str, amount: int, reference: str):
        """
        Initialize a transaction with Paystack.
        Amount must be in kobo (e.g., NGN 100.00 -> 10000).
        """
        url = f"{PAYSTACK_BASE_URL}/transaction/initialize"
        payload = {
            "email": email,
            "amount": amount,
            "reference": reference,
            "callback_url": f"{settings.BASE_URL}/payment-success"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()["data"]
            except httpx.HTTPStatusError as e:
                print(f"Paystack Error: {e.response.text}")
                raise ValueError("Payment initialization failed")

    async def verify_transaction(self, reference: str):
        """
        Verify the status of a transaction.
        """
        url = f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()["data"]
            except httpx.HTTPStatusError as e:
                print(f"Paystack Verification Error: {e.response.text}")
                raise ValueError("Payment verification failed")

paystack_client = PaystackService()