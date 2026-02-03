from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config.settings import get_settings
from src.db.models import Base

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        s = get_settings()
        _engine = create_engine(s.database_url, future=True)
    return _engine


def init_db() -> None:
    """
    Create tables (idempotent) and verify connectivity.
    """
    engine = get_engine()

    # Create all tables
    Base.metadata.create_all(engine)

    # Connectivity check
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
