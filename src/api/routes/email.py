"""
Email routes — test and status endpoints for the email alert system.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from src.services.email_service import is_email_configured, send_test_email

router = APIRouter()


class EmailStatusResponse(BaseModel):
    """Email configuration status."""
    configured: bool
    provider: str = "resend"
    from_address: str | None = None
    recipient: str | None = None


class EmailTestResponse(BaseModel):
    """Response from sending a test email."""
    status: str
    message: str
    email_id: str | None = None


@router.get("/email/status", response_model=EmailStatusResponse)
async def email_status():
    """Check if email alerts are configured."""
    import os

    if is_email_configured():
        return EmailStatusResponse(
            configured=True,
            from_address=os.getenv("ALERT_FROM_EMAIL", "onboarding@resend.dev"),
            recipient=os.getenv("ALERT_RECIPIENT_EMAIL", ""),
        )
    return EmailStatusResponse(configured=False)


@router.post("/email/test", response_model=EmailTestResponse)
async def test_email():
    """Send a test email to verify Resend configuration."""
    result = await send_test_email()
    return EmailTestResponse(**result)
