import httpx
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class PaystackService:
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = "https://api.paystack.co"
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
# ----------- external withdrawals------------------
    async def get_banks(self):
        """
        Fetching the list of supported banks by paystack
        """
        url = f"{self.base_url}/bank"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"Paystack bank list failed: {response.text}")
                return []
            
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Error fetching banks: {str(e)}")
            return []
        
    async def resolve_account(self, account_number: str, bank_code: str):
        url = f"{self.base_url}/bank/resolve"
        logger.info(f"Sending to Paystack -> Account: {account_number}, Bank: {bank_code}")

        params = {
            "account_number": account_number,
            "bank_code": bank_code
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params)

            logger.info(f"Generated Paystack URL: {response.url}")
            
            if response.status_code != 200:
                logger.error(f"Account resolution failed: {response.text}")
                return None
            return response.json()["data"]
    
        except Exception as e:
            logger.error(f"Error resolving account: {str(e)}")
            return None

    async def create_transfer_recipient(self, name: str, account_number: str, bank_code: str):
        """
        Register the beneficiary to get a Recipient Code (RCP_...).
        """
        url = f"{self.base_url}/transferrecipient"
        
        data = {
            "type": "nuban",
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=self.headers, json=data)
            
            if response.status_code not in [200, 201]:
                logger.error(f"Create Recipient Failed: {response.text}")
                return None
            
            return response.json()["data"]["recipient_code"]
            
        except Exception as e:
            logger.error(f"Error creating recipient: {str(e)}")
            return None

    async def initiate_transfer(self, amount: int, recipient_code: str, reference: str, reason: str):
        url = f"{self.base_url}/transfer"
        
        amount_kobo = amount * 100 
        
        data = {
            "source": "balance", 
            "amount": amount_kobo,
            "recipient": recipient_code,
            "reference": reference,
            "reason": reason
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=self.headers, json=data)
            
            if response.status_code not in [200, 201]:
                logger.error(f"Transfer Failed: {response.text}")
                return {"status": False, "message": response.text}
            
            return {"status": True, "data": response.json()["data"]}
            
        except Exception as e:
            logger.error(f"Error initiating transfer: {str(e)}")
            return {"status": False, "message": str(e)}
        
#-------------------- deposit-------------
    async def initialize_transaction(self, email: str, amount: int, reference: str):
        """
        Initialize a transaction with Paystack.
        """
        url = f"{self.base_url}/transaction/initialize"
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
        url = f"{self.base_url}/transaction/verify/{reference}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()["data"]
            except httpx.HTTPStatusError as e:
                print(f"Paystack Verification Error: {e.response.text}")
                raise ValueError("Payment verification failed")

paystack_client = PaystackService()