"""
Async SQLAlchemy engine and session factory for PostgreSQL / Supabase.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def _build_engine():
    settings = get_settings()
    url = settings.DATABASE_URL

    if "sqlite" in url:
        return create_async_engine(
            url,
            echo=settings.DEBUG,
            pool_pre_ping=True,
        )

    # Ensure asyncpg driver is used for PostgreSQL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    return create_async_engine(
        url,
        echo=settings.DEBUG,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )



engine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables defined in ORM models (used at startup)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
