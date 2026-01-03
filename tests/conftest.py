import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from app.main import app
from app.database import get_session
from app.models.core import User, Wallet
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

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    user_id = uuid.uuid4()
    
    user = User(
        id=user_id,
        email="test@example.com", 
        full_name="Test User"
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