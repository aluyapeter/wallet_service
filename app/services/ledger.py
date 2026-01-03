from sqlmodel import Session, select, func
from app.models.ledger import LedgerEntry
import uuid

class LedgerService:
    def get_current_balance(self, session: Session, wallet_id: uuid.UUID) -> int:
        """
        Calculates the live balance by summing all ledger entries.
        Returns 0 if no entries exist.
        """
        statement = select(func.sum(LedgerEntry.amount)).where(LedgerEntry.wallet_id == wallet_id)
        
        result = session.exec(statement).one()
        
        return result if result is not None else 0