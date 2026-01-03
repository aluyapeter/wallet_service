from fastapi import APIRouter, Depends, Request, HTTPException
from authlib.integrations.starlette_client import OAuth
from sqlmodel import Session

from app.database import get_session
from app.config import settings
from app.services.user_service import get_or_create_user
from app.security import create_access_token, get_current_user, get_pin_hash
from app.schemas import PINCreate
from app.models.core import User
from app.limiter import limiter

router = APIRouter()

oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@router.get("/auth/google")
async def login_google(request: Request):
    """
    Returns the Google Login URL.
    Copy this URL and paste it in a new tab (same browser) to login.
    """
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    response = await oauth.create_client('google').authorize_redirect(request, redirect_uri) #type: ignore
    
    return {"url": response.headers["location"]}

@router.get("/auth/google/callback")
async def auth_google(request: Request, session: Session = Depends(get_session)):
    """
    Handles the callback from Google.
    Exchanges the code for a token, gets user info, and logs them in.
    """
    try:
        token = await oauth.create_client('google').authorize_access_token(request) #type: ignore
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google Auth failed: {str(e)}")

    user_info = token.get('userinfo')
    
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to retrieve user info from Google")

    email = user_info.get('email')
    name = user_info.get('name')

    user = get_or_create_user(session, email, name)

    access_token = create_access_token(subject=user.id)

    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "email": user.email,
            "wallet_number": user.wallet.wallet_number if user.wallet else None
        }
    }

@router.post("/auth/set-pin")
@limiter.limit("5/hour")
def set_pin(
    request: Request,
    pin_data: PINCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session) 
):
    if user.pin_hash is not None:
        raise HTTPException(status_code=400, detail="PIN already set. Use change-pin endpoint")
    
    hashed_pin = get_pin_hash(pin_data.pin)
    user.pin_hash = hashed_pin

    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "status": "success",
        "message": "Transaction PIN secured."
    }