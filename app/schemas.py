from pydantic import BaseModel, Field, EmailStr, model_validator
from typing import List
import uuid
from sqlmodel import SQLModel

class UserSignup(SQLModel):
    full_name: str
    email: EmailStr
    password: str
    confirm_password: str

    @model_validator(mode='after')
    def check_passwords_match(self):
        pw = self.password
        cpw = self.confirm_password
        
        if pw is not None and cpw is not None and pw != cpw:
            raise ValueError('Passwords do not match')
        
        return self
    
class EmailVerification(SQLModel):
    email: EmailStr
    otp: str

class LoginRequest(SQLModel):
    email: EmailStr
    password: str

class ResendOTPRequest(BaseModel):
    email: EmailStr

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

class WithdrawalRequest(BaseModel):
    amount: int = Field(gt=0, description="Amount in Naira")
    account_number: str = Field(min_length=10, max_length=10)
    bank_code: str
    account_name: str
    pin: str

class ForgotPinRequest(SQLModel):
    email: EmailStr

class ResetPinRequest(SQLModel):
    email: EmailStr
    new_pin: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")
    otp: str

class PasswordReset(SQLModel):
    email: EmailStr
    otp: str
    password: str
    confirm_password: str

    @model_validator(mode='after')
    def check_passwords_match(self):
        pw = self.password
        cpw = self.confirm_password
        
        if pw is not None and cpw is not None and pw != cpw:
            raise ValueError('Passwords do not match')
        
        return self