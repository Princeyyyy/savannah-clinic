from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase


def utc_now() -> datetime:
    """Returns current naive UTC datetime for SQLAlchemy column defaults."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass
