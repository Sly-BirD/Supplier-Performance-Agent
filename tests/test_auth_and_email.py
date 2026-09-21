"""
Tests for Clerk Authentication dependency and Resend Email Service.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.auth import AuthenticatedUser, _is_auth_enabled, require_auth, get_current_user
from src.services.email_service import is_email_configured, send_alert_email
from src.api.main import app


class TestAuthModule:
    """Test Clerk authentication helpers."""

    def test_auth_disabled_when_keys_not_set(self, monkeypatch):
        monkeypatch.setenv("CLERK_SECRET_KEY", "")
        monkeypatch.setenv("CLERK_ISSUER", "")
        assert not _is_auth_enabled()

    @pytest.mark.asyncio
    async def test_require_auth_dev_mode_fallback(self, monkeypatch):
        monkeypatch.setenv("CLERK_SECRET_KEY", "")
        monkeypatch.setenv("CLERK_ISSUER", "")
        user = await require_auth(user=None)
        assert user is not None
        assert user.user_id == "dev-user"
        assert user.email == "dev@localhost"


class TestEmailService:
    """Test Resend email service helpers."""

    def test_email_configured_status(self, monkeypatch):
        monkeypatch.setenv("RESEND_API_KEY", "")
        assert not is_email_configured()

        monkeypatch.setenv("RESEND_API_KEY", "re_test_12345")
        monkeypatch.setenv("ALERT_RECIPIENT_EMAIL", "alerts@example.com")
        assert is_email_configured()

    @pytest.mark.asyncio
    async def test_send_email_graceful_noop_when_not_configured(self, monkeypatch):
        monkeypatch.setenv("RESEND_API_KEY", "")
        monkeypatch.setenv("ALERT_RECIPIENT_EMAIL", "")
        success = await send_alert_email(
            supplier_name="Test Supplier",
            alert_title="Critical Defect Spike",
            severity="CRITICAL",
            metric_value=24.5,
            threshold_value=5.0,
            suggested_action="Hold pending shipments and inspect lot.",
        )
        assert success is False


class TestEmailEndpoint:
    """Test email API route."""

    @pytest.mark.asyncio
    async def test_email_status_endpoint(self):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/email/status")
            assert resp.status_code == 200
            data = resp.json()
            assert "configured" in data
            assert data["provider"] == "resend"
            assert "from_address" in data
