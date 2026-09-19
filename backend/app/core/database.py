"""
Async SQLAlchemy engine and session factory for PostgreSQL / Supabase.

SQLite note: uses NullPool (one connection per checkout) + WAL journal mode +
30-second busy_timeout PRAGMA to prevent "database is locked" errors when
multiple async coroutines attempt concurrent writes.
"""
import asyncio
import logging
from collections.abc import AsyncGenerator

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def _build_engine():
    settings = get_settings()
    url = settings.DATABASE_URL

    if "sqlite" in url:
        # NullPool: each coroutine gets its own connection — prevents shared
        # connection contention that causes "database is locked" errors.
        # WAL mode + busy_timeout are applied via PRAGMAs on each connection.
        return create_async_engine(
            url,
            echo=settings.DEBUG,
            connect_args={
                "check_same_thread": False,
                "timeout": 30,           # busy_timeout in seconds
            },
            poolclass=NullPool,
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


def _configure_sqlite(engine):
    """
    Apply SQLite performance + concurrency pragmas on each new connection.
    - journal_mode=WAL : readers don't block writers; writers don't block readers.
    - synchronous=NORMAL: safe for local dev (commits survive power loss).
    - busy_timeout is already set via connect_args["timeout"].
    """
    from sqlalchemy import event, text

    if "sqlite" not in str(engine.url):
        return

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()


engine = _build_engine()
_configure_sqlite(engine)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


_SQLITE_RETRY_MAX = 3
_SQLITE_RETRY_DELAY = 0.5  # seconds — doubles each retry


def _is_sqlite_locked(exc: Exception) -> bool:
    """Return True if the exception is a transient SQLite 'database is locked' error."""
    return isinstance(exc, OperationalError) and "database is locked" in str(exc)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session with SQLite retry logic."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Retry commit if SQLite reports a transient lock
            for attempt in range(_SQLITE_RETRY_MAX):
                try:
                    await session.commit()
                    break
                except Exception as commit_exc:
                    if _is_sqlite_locked(commit_exc) and attempt < _SQLITE_RETRY_MAX - 1:
                        logger.warning(
                            "SQLite locked on commit (attempt %d/%d), retrying...",
                            attempt + 1, _SQLITE_RETRY_MAX,
                        )
                        await asyncio.sleep(_SQLITE_RETRY_DELAY * (2 ** attempt))
                        continue
                    await session.rollback()
                    raise
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables defined in ORM models (used at startup)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
