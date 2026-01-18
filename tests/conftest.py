# tests/conftest.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from app.main import app
from app.database import get_session
from app.core.redis import get_redis
from app.models.core import User, Wallet
from app.security import get_pin_hash
from httpx import AsyncClient, ASGITransport
import uuid

sqlite_file_name = "database.db"
sqlite_url = "sqlite://"

engine = create_engine(
    sqlite_url, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="mock_redis")
def mock_redis_fixture():
    """
    Creates a fake Redis that just stores data in a Python dictionary.
    This prevents us from needing a real Redis server running for tests.
    """
    mock = AsyncMock()
    mock.get.return_value = None 
    return mock

@pytest.fixture(name="mock_email_service")
def mock_email_service_fixture(monkeypatch):
    """
     intercepts 'app.tasks.send_email_task' so no emails are sent.
    """
    mock = MagicMock()
    monkeypatch.setattr("app.tasks.send_email_task.delay", mock)
    return mock

@pytest.fixture(name="client")
def client_fixture(session: Session, mock_redis):
    def get_session_override():
        return session
    
    async def get_redis_override():
        return mock_redis

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_redis] = get_redis_override
    
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    user_id = uuid.uuid4()
    
    hashed_pwd = get_pin_hash("testpassword") 
    hashed_pin = get_pin_hash("1234")

    user = User(
        id=user_id,
        email="test@example.com", 
        full_name="Test User",
        password_hash=hashed_pwd,
        pin_hash=hashed_pin,
        is_email_verified=True
    )
    session.add(user)
    session.commit()
    
    wallet = Wallet(
        wallet_number="1234567890", 
        balance=50000, 
        user_id=user_id
    )
    session.add(wallet)
    session.commit()
    
    session.refresh(user)
    return user

@pytest.fixture(name="async_client")
async def async_client_fixture(session, mock_redis):
    """
    Creates an AsyncClient that ALSO overrides dependencies.
    This ensures async tests use the Fake DB and Fake Redis.
    """
    def get_session_override():
        return session
    
    async def get_redis_override():
        return mock_redis

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_redis] = get_redis_override
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()