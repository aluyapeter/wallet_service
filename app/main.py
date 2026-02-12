from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from .limiter import limiter
from slowapi.errors import RateLimitExceeded
from app.database import create_db_and_tables
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings
from app.routers import auth, keys, wallet, banks
from fastapi.middleware.cors import CORSMiddleware
from app.middleware import IdempotencyMiddleware
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup: Creating database tables...")
    create_db_and_tables()
    yield
    print("Shutdown: cleaning up...")

app = FastAPI(lifespan=lifespan)
app.include_router(auth.router)
app.include_router(keys.router)
app.include_router(wallet.router)
app.include_router(banks.router)

@app.middleware("http")
async def log_request_time(request: Request, call_next):
    start = time.time()

    response = await call_next(request)

    duration_ms = (time.time() - start) * 1000
    logger.info(
        f"[{request.method}] {request.url.path} → "
        f"{response.status_code} ({duration_ms:.1f}ms)"
    )

    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.1f}"
    return response

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) #type: ignore

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=False
)
app.add_middleware(IdempotencyMiddleware)

@app.get("/")
def read_root():
    return {"status":"ok", "service": "Wallet service"}

@app.get("/payment-success")
def payment_success(trxref: str | None = None, reference: str | None = None):
    """
    Landing page for users after they pay on Paystack.
    This does NOT credit the wallet. The Webhook handles that.
    """
    return {
        "message": "Payment successful! Your deposit is being processed.",
        "reference": reference
    }