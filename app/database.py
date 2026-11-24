"""SQLAlchemy engine, session factory, and declarative base."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

_engine_kwargs = {"pool_pre_ping": True, "future": True}
if not settings.database_url.startswith("sqlite"):
    # SQLite's default pool (SingletonThreadPool/NullPool) doesn't accept
    # pool_size/max_overflow -- those only apply to QueuePool, used for
    # real PostgreSQL connections. SQLite is only ever used in the test
    # suite (see tests/conftest.py), never in local dev or production.
    _engine_kwargs.update(pool_size=5, max_overflow=10)

engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a database session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
