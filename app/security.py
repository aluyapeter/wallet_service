from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional, List
from dataclasses import dataclass, field
from jose import jwt, JWTError
import uuid
from pwdlib import PasswordHash

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import User, APIKey
from app.utils import hash_api_key

security_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)
password_hash = PasswordHash.recommended()

@dataclass
class UserAuthContext:
    user: User
    permissions: List[str] = field(default_factory=list)
    is_admin: bool = False


def create_access_token(subject: Union[str, Any], expires_delta: Union[timedelta, None] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_user_from_jwt(token: str, session: Session) -> Optional[User]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    return session.get(User, uuid.UUID(user_id))

def get_user_from_api_key(api_key: str, session: Session) -> Optional[APIKey]:
    """
    Returns the APIKey record if valid, so we can access permissions.
    """
    hashed = hash_api_key(api_key)
    statement = select(APIKey).where(APIKey.key_hash == hashed)
    key_record = session.exec(statement).first()
    
    if not key_record or not key_record.is_active:
        return None
        
    db_expiry = key_record.expires_at
    if db_expiry.tzinfo is None:
        db_expiry = db_expiry.replace(tzinfo=timezone.utc)

    if db_expiry < datetime.now(timezone.utc):
        return None
    
    return key_record


def get_auth_context(
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    api_key_str: Optional[str] = Security(api_key_header),
    session: Session = Depends(get_session)
) -> UserAuthContext:
    """
    Determines if the request is from a Human (JWT) or a Service (API Key).
    Returns a context object containing the User and their Permissions.
    """
    if auth_creds:
        user = get_user_from_jwt(auth_creds.credentials, session)
        if user:
            return UserAuthContext(user=user, is_admin=True, permissions=[])

    if api_key_str:
        key_record = get_user_from_api_key(api_key_str, session)
        if key_record:
            return UserAuthContext(
                user=key_record.user, 
                permissions=key_record.permissions, 
                is_admin=False
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Provide a valid Bearer token or x-api-key.",
    )

def get_current_user(context: UserAuthContext = Depends(get_auth_context)) -> User:
    """
    For endpoints that just need the user and don't care about specific permissions.
    """
    return context.user

def require_permission(permission: str):
    """
    Factory for permission checking dependency.
    Usage: user: User = Depends(require_permission("deposit"))
    """
    def permission_checker(context: UserAuthContext = Depends(get_auth_context)) -> User:
        if context.is_admin:
            return context.user
        
        if permission not in context.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Missing required permission: '{permission}'"
            )
        return context.user
    return permission_checker

## hash password func
def verify_pin(plain_pin, hashed_pin):
    return password_hash.verify(plain_pin, hashed_pin)

def get_pin_hash(pin):
    return password_hash.hash(pin)