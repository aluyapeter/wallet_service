from sqlmodel import create_engine, SQLModel, Session
from app.config import settings

connection_string = str(settings.DATABASE_URL)
if connection_string.startswith("postgres://"):
    connection_string = connection_string.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    connection_string,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session