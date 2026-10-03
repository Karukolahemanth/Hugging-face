"""
Async SQLAlchemy database setup for GAIA Agent.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.database.models import Base
from backend.utils.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        # Convert sync sqlite:/// URL to async aiosqlite:///
        db_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        _engine = create_async_engine(db_url, echo=False, future=True)
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def init_db() -> None:
    """Create all tables if they don't exist."""
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialised.")


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async database session."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
