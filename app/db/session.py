from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# SQLite requires check_same_thread=False for multithreaded access
connect_args = (
    {"check_same_thread": False}
    if settings.normalized_database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.normalized_database_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
