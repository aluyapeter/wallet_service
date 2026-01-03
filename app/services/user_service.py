from sqlmodel import Session, select
from app.models.core import User, Wallet
import secrets
import string

def get_or_create_user(session: Session, email: str, full_name: str) -> User:
    """
    Finds a user by email or creates a new one with a linked wallet.
    Includes collision detection for wallet numbers.
    """
    statement = select(User).where(User.email == email)
    existing_user = session.exec(statement).first()
    
    if existing_user:
        return existing_user
    
    new_user = User(email=email, full_name=full_name)
    session.add(new_user)
    
    unique_wallet_number = None
    
    while True:
        candidate = ''.join(secrets.choice(string.digits) for _ in range(10))
        
        check_stmt = select(Wallet).where(Wallet.wallet_number == candidate)
        if not session.exec(check_stmt).first():
            unique_wallet_number = candidate
            break
            
    new_wallet = Wallet(
        wallet_number=unique_wallet_number,
        balance=0,
        user=new_user
    )
    session.add(new_wallet)
    session.commit()
    session.refresh(new_user)
    
    return new_user