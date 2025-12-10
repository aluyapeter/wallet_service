from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime

from app.database import get_session
from app.models import User, APIKey
from app.schemas import APIKeyCreate
from app.security import get_current_user
from app.utils import generate_api_key, hash_api_key, calculate_expiry
from app.schemas import APIKeyRollover, APIKeyCreate
from typing import List

router = APIRouter()

@router.post("/keys/create")
def create_api_key(
    request: APIKeyCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    Generates a new API Key for the authenticated user.
    Enforces a maximum of 5 active keys.
    """
    active_keys = [key for key in user.api_keys if key.is_active]
    
    if len(active_keys) >= 5:
        raise HTTPException(
            status_code=400, 
            detail="Limit reached. You cannot have more than 5 active API keys."
        )
    
    try:
        expires_at = calculate_expiry(request.expiry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    raw_key = generate_api_key()
    hashed_key = hash_api_key(raw_key)

    new_key = APIKey(
        name=request.name,
        key_hash=hashed_key,
        permissions=request.permissions,
        expires_at=expires_at,
        user_id=user.id,
        is_active=True
    )

    session.add(new_key)
    session.commit()
    session.refresh(new_key)

    return {
        "status": "success",
        "api_key": raw_key,
        "name": new_key.name,
        "permissions": new_key.permissions,
        "expires_at": new_key.expires_at
    }



@router.post("/keys/rollover")
def rollover_api_key(
    request: APIKeyRollover,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    Replaces an old/expired key with a new one inheriting the same permissions.
    """
    statement = select(APIKey).where(APIKey.id == request.expired_key_id)
    old_key = session.exec(statement).first()

    if not old_key or old_key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API Key not found")

    try:
        expires_at = calculate_expiry(request.expiry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    raw_key = generate_api_key()
    hashed_key = hash_api_key(raw_key)

    new_key = APIKey(
        name=f"{old_key.name} (Rolled Over)",
        key_hash=hashed_key,
        permissions=old_key.permissions, 
        expires_at=expires_at,
        user_id=user.id,
        is_active=True
    )

    old_key.is_active = False

    session.add(new_key)
    session.add(old_key)
    session.commit()
    session.refresh(new_key)

    return {
        "status": "success",
        "message": "Key rolled over successfully",
        "api_key": raw_key,
        "name": new_key.name,
        "permissions": new_key.permissions,
        "expires_at": new_key.expires_at
    }


@router.get("/keys", response_model=List[dict])
def list_api_keys(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    List all API keys owned by the user.
    """
    return [
        {
            "id": key.id,
            "name": key.name,
            "prefix": "sk_live_...",
            "is_active": key.is_active,
            "expires_at": key.expires_at
        }
        for key in user.api_keys
    ]