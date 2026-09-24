"""SQLAlchemy engine, declarative base, and request-scoped sessions."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for persisted application models."""


engine: Engine | None = (
    create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    if settings.DATABASE_URL
    else None
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False) if engine else None


def get_db() -> Generator[Session, None, None]:
    """Yield a database session or fail clearly when PostgreSQL is not configured."""
    if SessionLocal is None:
        raise RuntimeError("Database access is unavailable: DATABASE_URL is not configured")
    with SessionLocal() as session:
        yield session
