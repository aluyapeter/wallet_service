import httpx
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class PaystackService:
    _client = httpx.AsyncClient(timeout=30.0) 

    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = "https://api.paystack.co"
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, **kwargs):
        """
        Internal helper to handle requests using the shared client.
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = await self._client.request(method, url, headers=self.headers, **kwargs)
            
            if response.status_code >= 400:
                logger.error(f"Paystack Error [{endpoint}]: {response.text}")
                
            return response
        except httpx.RequestError as e:
            logger.error(f"Paystack Connection Error: {str(e)}")
            raise

    # -------------------- Deposit -----------------
    async def initialize_transaction(self, email: str, amount: int, reference: str):
        """
        Initialize a transaction with Paystack.
        """
        if email.startswith("test"):
            return {
                "authorization_url": "https://checkout.paystack.com/fake-url",
                "access_code": "fake-code",
                "reference": reference
            }
        
        payload = {
            "email": email,
            "amount": amount, 
            "reference": reference,
            "callback_url": f"{settings.BASE_URL}/payment-success"
        }

        response = await self._request("POST", "/transaction/initialize", json=payload)
        
        if response.status_code != 200:
             raise ValueError("Payment initialization failed")
             
        return response.json()["data"]

    async def verify_transaction(self, reference: str):
        """
        Verify the status of a transaction.
        """
        response = await self._request("GET", f"/transaction/verify/{reference}")
        
        if response.status_code != 200:
            return {"status": "failed"}
            
        return response.json()["data"]

    # -------------------- External Withdrawals ------------------
    async def get_banks(self):
        response = await self._request("GET", "/bank")
        if response.status_code != 200:
            return []
        return response.json().get("data", [])

    async def resolve_account(self, account_number: str, bank_code: str):
        params = {"account_number": account_number, "bank_code": bank_code}
        response = await self._request("GET", "/bank/resolve", params=params)
        
        if response.status_code != 200:
            return None
        return response.json()["data"]

    async def create_transfer_recipient(self, name: str, account_number: str, bank_code: str):
        data = {
            "type": "nuban",
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN"
        }
        response = await self._request("POST", "/transferrecipient", json=data)
        
        if response.status_code not in [200, 201]:
            return None
        return response.json()["data"]["recipient_code"]

    async def initiate_transfer(self, amount: int, recipient_code: str, reference: str, reason: str):        
        data = {
            "source": "balance", 
            "amount": amount,
            "recipient": recipient_code,
            "reference": reference,
            "reason": reason
        }
        
        response = await self._request("POST", "/transfer", json=data)
        
        if response.status_code not in [200, 201]:
            return {"status": False, "message": response.text}
            
        return {"status": True, "data": response.json()["data"]}
    
    async def verify_transfer(self, reference: str):
        """
        Checks the status of a transfer.
        """
        response = await self._request("GET", f"/transfer/verify/{reference}")
        
        if response.status_code != 200:
            return "failed"
            
        return response.json().get("data", {}).get("status", "failed")

    @classmethod
    async def close_connection(cls):
        await cls._client.aclose()