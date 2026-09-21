"""
Authentication — Clerk JWT verification for FastAPI.

Provides a `get_current_user` dependency that:
1. Extracts the Bearer token from the Authorization header
2. Fetches Clerk's JWKS (cached) to get the RS256 public key
3. Verifies and decodes the JWT
4. Returns the authenticated user's ID

When CLERK_SECRET_KEY is not set, auth is bypassed (dev mode).
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional

import httpx
import jwt as pyjwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Request, status

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def get_clerk_secret_key() -> str:
    return os.getenv("CLERK_SECRET_KEY", "")


def get_clerk_issuer() -> str:
    return os.getenv("CLERK_ISSUER", "")


def _is_auth_enabled() -> bool:
    """Check if Clerk authentication is configured."""
    return bool(get_clerk_secret_key() and get_clerk_issuer())


# Lazy-initialized JWKS client (cached in memory)
_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> PyJWKClient:
    """Get or initialize the JWKS client for Clerk's public keys."""
    global _jwks_client
    issuer = get_clerk_issuer()
    if _jwks_client is None:
        if not issuer:
            raise ValueError(
                "CLERK_ISSUER is not set. "
                "Set it to your Clerk Frontend API URL (e.g., https://your-app.clerk.accounts.dev)"
            )
        jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


@dataclass
class AuthenticatedUser:
    """Represents a verified Clerk user extracted from a JWT."""
    user_id: str
    session_id: str | None = None
    email: str | None = None


async def get_current_user(request: Request) -> AuthenticatedUser | None:
    """
    FastAPI dependency: verify the Clerk JWT from the Authorization header.

    Behavior:
    - If CLERK_SECRET_KEY is not set → returns None (dev mode, no auth enforced)
    - If token is present and valid → returns AuthenticatedUser
    - If token is missing or invalid → raises 401
    """
    if not _is_auth_enabled():
        # Dev mode: auth not configured, allow all requests
        return None

    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[len("Bearer "):]

    try:
        # Get the signing key from Clerk's JWKS endpoint
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        issuer = get_clerk_issuer()
        payload = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": False,  # Clerk doesn't always set audience
            },
        )

        user_id = payload.get("sub", "")
        session_id = payload.get("sid")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )

        return AuthenticatedUser(
            user_id=user_id,
            session_id=session_id,
        )

    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except pyjwt.InvalidTokenError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected auth error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        )


async def require_auth(user: AuthenticatedUser | None = Depends(get_current_user)) -> AuthenticatedUser:
    """
    Stricter dependency: always requires an authenticated user.
    Use this on routes that must never be accessible without auth.

    In dev mode (no Clerk keys), returns a placeholder user.
    """
    if user is None:
        if not _is_auth_enabled():
            # Dev mode fallback: return a dummy user
            return AuthenticatedUser(user_id="dev-user", email="dev@localhost")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user
