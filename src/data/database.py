"""
Database session management and engine configuration.

Supports:
- Neon PostgreSQL (production) via asyncpg
- Local SQLite (development fallback) via aiosqlite
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from dotenv import load_dotenv

load_dotenv()

raw_url = os.getenv("DATABASE_URL") or "sqlite+aiosqlite:///./supplier_performance.db"

_is_sqlite = "sqlite" in raw_url

if not _is_sqlite:
    # Ensure asyncpg driver prefix
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+asyncpg://"):
        raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Clean query parameters that asyncpg doesn't accept directly in DSN
    parsed = urlparse(raw_url)
    params = parse_qs(parsed.query)
    params.pop("sslmode", None)
    params.pop("channel_binding", None)
    new_query = urlencode(params, doseq=True)
    DATABASE_URL = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))
else:
    DATABASE_URL = raw_url

# Build engine kwargs based on database type
_engine_kwargs: dict = {
    "echo": os.getenv("APP_ENV") == "development",
}

if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL (Neon) optimized settings
    _engine_kwargs.update({
        "pool_pre_ping": True,        # Verify connections before use (handles Neon idle timeouts)
        "pool_size": 5,               # Baseline connection pool
        "max_overflow": 10,           # Burst capacity
        "pool_recycle": 300,          # Recycle connections every 5 min (Neon drops idle conns)
        "pool_timeout": 30,           # Wait up to 30s for a connection from the pool
        "connect_args": {"ssl": "require"},  # Required for Neon cloud SSL connections
    })

engine: AsyncEngine = create_async_engine(DATABASE_URL, **_engine_kwargs)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency-injectable async session generator."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context-manager variant for use outside FastAPI dependency injection."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables. Used for development/testing; production uses Alembic."""
    from src.data import models  # noqa: F401 - ensure models are registered on Base.metadata

    global engine, async_session_factory
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        # If connecting to external database fails in development, fallback to SQLite
        if os.getenv("APP_ENV") == "development" and "sqlite" not in str(engine.url):
            print(f"\n⚠️  [WARN] Failed to connect to database ({engine.url}): {exc}")
            print("📦 [INFO] Falling back to local SQLite: sqlite+aiosqlite:///./supplier_performance.db\n")
            sqlite_url = "sqlite+aiosqlite:///./supplier_performance.db"
            engine = create_async_engine(
                sqlite_url,
                connect_args={"check_same_thread": False},
            )
            async_session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            raise


async def dispose_db() -> None:
    """Dispose of the engine connection pool."""
    await engine.dispose()
