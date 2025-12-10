from pydantic import BaseModel
from typing import List
import uuid

class APIKeyCreate(BaseModel):
    name: str
    permissions: List[str]
    expiry: str

class TransferRequest(BaseModel):
    wallet_number: str
    amount: int
    description: str = "Transfer"

class DepositRequest(BaseModel):
    amount: int

class APIKeyRollover(BaseModel):
    expired_key_id: uuid.UUID
    expiry: str