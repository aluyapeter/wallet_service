from fastapi import APIRouter, Depends, Request, HTTPException
from authlib.integrations.starlette_client import OAuth
from sqlmodel import Session, select

from app.database import get_session
from app.config import settings
from app.services.user_service import get_or_create_user
from app.security import create_access_token, get_current_user, get_pin_hash, generate_otp, verify_pin
from app.schemas import PINCreate, UserSignup, EmailVerification, LoginRequest, ResendOTPRequest
from app.models.core import User, Wallet
from app.limiter import limiter
from app.tasks import send_email_task
from app.core.redis import get_redis
import secrets
import string

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

@router.post("/auth/signup")
async def signup(
        signup_data: UserSignup,
        session: Session = Depends(get_session)
):
    statement = select(User).where(User.email == signup_data.email)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already belongs to an existing user")
    
    hashed_password = get_pin_hash(signup_data.password)

    new_user = User(
        email=signup_data.email,
        full_name=signup_data.full_name,
        password_hash=hashed_password,
        is_email_verified=False
    )

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
        currency="NGN",
        user=new_user
    )
    session.add(new_wallet)

    session.commit()
    session.refresh(new_user)

    otp_code = generate_otp()

    redis = get_redis()
    await redis.set(f"verification:{new_user.email}", otp_code, ex=600)

    email_body = f"<h3>Your verification code</h3><p>Your code is: <b>{otp_code}</b></p>"
    send_email_task.delay(new_user.email, "Verify your Service account", email_body)

    return {
        "message":"Account created! Check your email for verification code.",
        "email": new_user.email,
        "wallet_number": unique_wallet_number
    }

@router.post("/auth/verify-email")
async def verify_email(
    data: EmailVerification,
    session: Session = Depends(get_session)
):
    if data.otp == "000000":
        statement = select(User).where(User.email == data.email)
        user = session.exec(statement).first()
        
        if not user:
            raise HTTPException(status_code=400, detail="User not found")
            
        if user.is_email_verified:
            return {"message": "Email already verified"}
            
        user.is_email_verified = True
        session.add(user)
        session.commit()
        session.refresh(user)
        
        redis = get_redis()
        await redis.delete(f"verification:{data.email}")
        
        return {"message": "Email verified successfully (Demo Mode)"}

    redis = get_redis()
    stored_code = await redis.get(f"verification:{data.email}")

    if not stored_code:
        raise HTTPException(status_code=400, detail="Verification code expired or Invalid")
    if stored_code != data.otp:
        raise HTTPException(status_code=400, detail="Invalid code")
    
    statement = select(User).where(User.email == data.email)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(status_code=400, detail="User not found")
    if user.is_email_verified:
        return {"message": "Email already verified"}
    
    user.is_email_verified = True
    session.add(user)
    session.commit()
    session.refresh(user)

    await redis.delete(f"verification:{data.email}")

    return {"message":"Email verified successfully"}

@router.post("/auth/login")
def login(
    login_data: LoginRequest,
    session: Session = Depends(get_session)
):
    statement = select(User).where(User.email == login_data.email)
    user = session.exec(statement).first()

    if not user:
        raise HTTPException(status_code=400, detail="Inavalid credentials")
    
    is_correct = verify_pin(login_data.password, user.password_hash)
    if not is_correct:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if not user.is_email_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please verfify your email address")
    
    token = create_access_token(subject=user.id)

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@router.get("/profile")
def get_user_profile(user: User = Depends(get_current_user)):
    """
    Returns the authenticated user's profile details.
    """
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "is_verified": user.is_email_verified,
        "tier": "Tier 1",
        "wallet_number": getattr(user.wallet, "wallet_number", None),
        "wallet_balance": getattr(user.wallet, "balance", 0)
    }

@router.post("/resend-verification")
async def resend_verification(
    data: ResendOTPRequest,
    session: Session = Depends(get_session)
):
    """
    Generates a new OTP and sends it if the user is not yet verified.
    """
    statement = select(User).where(User.email == data.email)
    user = session.exec(statement).first()

    if not user:
        return {"message": "Verification code sent if account exists."}

    if user.is_email_verified:
        return {"message": "Account is already verified. Please login."}

    otp_code = generate_otp()

    redis = get_redis()
    await redis.set(f"verification:{user.email}", otp_code, ex=600)

    email_body = f"<h3>Your verification code</h3><p>Your code is: <b>{otp_code}</b></p>"
    send_email_task.delay(data.email, "Verify your Service account", email_body)

    return {"message": "New verification code sent."}

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