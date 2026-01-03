from sqlmodel import SQLModel, Field
import uuid
from datetime import datetime, timezone

class LedgerEntry(SQLModel, table=True):
    __tablename__ = "ledger_entry" #type: ignore

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    wallet_id: uuid.UUID = Field(foreign_key="wallet.id", index=True)
    amount: int
    transaction_id: uuid.UUID = Field(foreign_key="transaction.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))