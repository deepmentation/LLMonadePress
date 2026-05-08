from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lemonade.models import Base

_engine = None
_async_session = None


def get_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://lemonade:changeme@localhost:5432/lemonade",
    )


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_database_url(), echo=False)
    return _engine


def get_session_factory():
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session


def reset_engine() -> None:
    """Reset engine and session factory. Useful for tests that override DATABASE_URL."""
    global _engine, _async_session
    _engine = None
    _async_session = None


async def init_db() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        yield session
