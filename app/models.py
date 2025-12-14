from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON, BigInteger

class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    TRANSFER = "transfer"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    wallet: Optional["Wallet"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False}
    )
    api_keys: List["APIKey"] = Relationship(back_populates="user")
    pin_hash: str | None = Field(default=None)

class Wallet(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    wallet_number: str = Field(unique=True, index=True)
    balance: int = Field(sa_column=Column(BigInteger), default=0)
    currency: str = Field(default="NGN")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", unique=True)
    user: User = Relationship(back_populates="wallet")
    transactions: List["Transaction"] = Relationship(back_populates="wallet")

class Transaction(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    amount: int = Field(sa_column=Column(BigInteger))
    transaction_type: TransactionType
    status: TransactionStatus = Field(default=TransactionStatus.PENDING)
    reference: str = Field(unique=True, index=True)
    meta_data: Optional[Dict[str, Any]] = Field(default={}, sa_column=Column(JSON)) 
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    wallet_id: uuid.UUID = Field(foreign_key="wallet.id")
    wallet: Wallet = Relationship(back_populates="transactions")

class APIKey(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    key_hash: str
    permissions: List[str] = Field(sa_column=Column(JSON), default=[])
    
    is_active: bool = Field(default=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user_id: uuid.UUID = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="api_keys")