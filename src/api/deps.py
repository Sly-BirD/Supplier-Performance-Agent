"""
FastAPI dependency injection — database sessions, auth, and tenant context.
"""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.database import async_session_factory
from src.api.auth import AuthenticatedUser, get_current_user, require_auth


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for request handlers."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_user_id(
    user: AuthenticatedUser = Depends(require_auth),
) -> str:
    """
    Extract the authenticated user's ID for tenant-scoped queries.

    Returns the Clerk user_id from the JWT, or 'dev-user' in dev mode.
    Every data-accessing route should depend on this to ensure isolation.
    """
    return user.user_id


__all__ = ["get_db", "get_current_user", "require_auth", "get_user_id", "AuthenticatedUser"]

