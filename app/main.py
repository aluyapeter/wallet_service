from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import create_db_and_tables
from starlette.middleware.sessions import SessionMiddleware
from app import models
from app.config import settings
from app.routers import auth, keys, wallet

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


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY
)

@app.get("/")
def read_root():
    return {"status":"ok", "service": "Wallet service"}

@app.get("/payment-success")
def payment_success(trxref: str | None = None, reference: str | None = None):
    """
    Landing page for users after they pay on Paystack.
    Note: This does NOT credit the wallet. The Webhook does that.
    """
    return {
        "status": "success",
        "message": "Payment successful! Your deposit is being processed.",
        "reference": reference
    }