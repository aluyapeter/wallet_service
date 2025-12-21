from pydantic import BaseModel, Field
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
    pin: str

class DepositRequest(BaseModel):
    amount: int

class APIKeyRollover(BaseModel):
    expired_key_id: uuid.UUID
    expiry: str

class APIKeyRevoke(BaseModel):
    key_id: uuid.UUID

class PINCreate (BaseModel):
    pin: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")