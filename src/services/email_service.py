"""
Email Service — Resend-powered alert notification system.

Sends formatted HTML emails when HIGH or CRITICAL alerts fire.
Gracefully no-ops when RESEND_API_KEY is not configured.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_resend_api_key() -> str:
    return os.getenv("RESEND_API_KEY", "")


def get_alert_recipient() -> str:
    return os.getenv("ALERT_RECIPIENT_EMAIL", "")


def get_alert_from_email() -> str:
    return os.getenv("ALERT_FROM_EMAIL", "onboarding@resend.dev")


def is_email_configured() -> bool:
    """Check if email sending is properly configured."""
    return bool(get_resend_api_key() and get_alert_recipient())


@dataclass
class AlertEmailData:
    """Data needed to compose an alert email."""
    alert_id: str
    supplier_name: str
    rule_type: str
    severity: str
    title: str
    description: str
    metric_value: float
    threshold_value: float
    suggested_action: str


def _build_alert_html(data: AlertEmailData) -> str:
    """Build a styled HTML email body for an alert notification."""
    severity_colors = {
        "critical": "#ef4444",
        "high": "#f97316",
        "medium": "#eab308",
        "low": "#3b82f6",
    }
    color = severity_colors.get(data.severity.lower(), "#6b7280")

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0; padding:0; background:#0a0a0f; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <div style="max-width:600px; margin:0 auto; padding:32px 24px;">
            <!-- Header -->
            <div style="text-align:center; margin-bottom:32px;">
                <h1 style="color:#f0f0f5; font-size:20px; margin:0;">
                    SIGNAL INTELLIGENCE
                </h1>
                <p style="color:#71717a; font-size:12px; margin-top:4px; letter-spacing:1px; text-transform:uppercase;">
                    Automated Supplier Performance Alert
                </p>
            </div>

            <!-- Card -->
            <div style="background:#12121a; border:1px solid #27272a; border-radius:8px; padding:24px; margin-bottom:24px;">
                <!-- Severity Badge -->
                <div style="margin-bottom:16px;">
                    <span style="background:{color}22; color:{color}; border:1px solid {color}44; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:700; letter-spacing:1px; text-transform:uppercase;">
                        {data.severity}
                    </span>
                    <span style="color:#71717a; font-size:12px; margin-left:8px;">
                        Rule: {data.rule_type}
                    </span>
                </div>

                <!-- Alert Title -->
                <h2 style="color:#f0f0f5; font-size:18px; margin:0 0 8px 0;">
                    {data.title}
                </h2>

                <!-- Supplier Name -->
                <p style="color:#a1a1aa; font-size:14px; margin:0 0 16px 0;">
                    Supplier: <strong style="color:#f0f0f5;">{data.supplier_name}</strong>
                </p>

                <!-- Description -->
                <p style="color:#d4d4d8; font-size:13px; line-height:1.5; margin:0 0 20px 0;">
                    {data.description}
                </p>

                <!-- Metric Comparison -->
                <div style="background:#181825; border:1px solid #27272a; border-radius:6px; padding:16px; margin-bottom:20px;">
                    <table style="width:100%; border-collapse:collapse;">
                        <tr>
                            <td style="color:#71717a; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; padding-bottom:6px;">Current Value</td>
                            <td style="color:#71717a; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; padding-bottom:6px; text-align:right;">Threshold</td>
                        </tr>
                        <tr>
                            <td style="color:{color}; font-size:22px; font-weight:700; font-family:monospace;">
                                {data.metric_value:.1f}
                            </td>
                            <td style="color:#a1a1aa; font-size:22px; font-weight:700; font-family:monospace; text-align:right;">
                                {data.threshold_value:.1f}
                            </td>
                        </tr>
                    </table>
                </div>

                <!-- Suggested Action -->
                {f'''
                <div style="background:#1c1917; border-left:3px solid #f97316; padding:12px 16px; border-radius:0 6px 6px 0; margin-bottom:16px;">
                    <div style="color:#f97316; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">
                        Recommended Action
                    </div>
                    <div style="color:#e4e4e7; font-size:13px; line-height:1.4;">
                        {data.suggested_action}
                    </div>
                </div>
                ''' if data.suggested_action else ''}
            </div>

            <!-- Footer -->
            <div style="text-align:center; padding-top:16px; border-top:1px solid #1f1f2e;">
                <p style="color:#52525b; font-size:11px; margin:0 0 4px 0;">
                    This alert was automatically generated by Signal Supplier Performance Agent.
                </p>
                <p style="color:#3f3f46; font-size:10px; margin:0;">
                    Alert ID: {data.alert_id}
                </p>
            </div>
        </div>
    </body>
    </html>
    """


async def send_alert_email(
    data: AlertEmailData | None = None,
    *,
    alert_id: str = "",
    supplier_name: str = "",
    rule_type: str = "custom",
    severity: str = "high",
    alert_title: str = "",
    title: str = "",
    description: str = "",
    metric_value: float = 0.0,
    threshold_value: float = 0.0,
    suggested_action: str = "",
) -> bool:
    """
    Send an alert notification email via Resend.

    Returns True if sent successfully, False otherwise.
    Silently no-ops if Resend is not configured.
    """
    if not is_email_configured():
        logger.debug("Email not configured (RESEND_API_KEY or ALERT_RECIPIENT_EMAIL missing). Skipping.")
        return False

    if data is None:
        data = AlertEmailData(
            alert_id=alert_id,
            supplier_name=supplier_name,
            rule_type=rule_type,
            severity=severity,
            title=title or alert_title,
            description=description,
            metric_value=metric_value,
            threshold_value=threshold_value,
            suggested_action=suggested_action,
        )

    try:
        import resend

        resend.api_key = get_resend_api_key()

        severity_emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "📋",
            "low": "ℹ️",
        }
        emoji = severity_emoji.get(data.severity.lower(), "📋")

        html_body = _build_alert_html(data)

        params: resend.Emails.SendParams = {
            "from": get_alert_from_email(),
            "to": [get_alert_recipient()],
            "subject": f"{emoji} [{data.severity.upper()}] {data.title} — {data.supplier_name}",
            "html": html_body,
        }

        email_response = resend.Emails.send(params)
        logger.info(
            f"Alert email sent for '{data.title}' (supplier: {data.supplier_name}) "
            f"→ {get_alert_recipient()} [id: {email_response.get('id', 'unknown')}]"
        )
        return True

    except ImportError:
        logger.warning("resend package not installed. Run: pip install resend")
        return False
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}", exc_info=True)
        return False


async def send_test_email() -> dict:
    """
    Send a test email to verify Resend configuration.
    Returns a dict with status and details.
    """
    if not is_email_configured():
        return {
            "status": "not_configured",
            "message": "Email is not configured. Set RESEND_API_KEY and ALERT_RECIPIENT_EMAIL in .env",
        }

    try:
        import resend

        resend.api_key = get_resend_api_key()

        params: resend.Emails.SendParams = {
            "from": get_alert_from_email(),
            "to": [get_alert_recipient()],
            "subject": "✅ Signal — Email Configuration Test",
            "html": """
            <div style="font-family:sans-serif; padding:24px; background:#0a0a0f; color:#f0f0f5;">
                <h2>🎉 Email is working!</h2>
                <p style="color:#9ca3af;">
                    Your Signal Supplier Intelligence Platform is now configured to send
                    email alerts when critical supplier performance thresholds are breached.
                </p>
                <p style="color:#8b5cf6; font-weight:600;">
                    You will receive automatic notifications for HIGH and CRITICAL severity alerts.
                </p>
            </div>
            """,
        }

        email_response = resend.Emails.send(params)
        return {
            "status": "sent",
            "message": f"Test email sent to {get_alert_recipient()}",
            "email_id": email_response.get("id"),
        }

    except ImportError:
        return {"status": "error", "message": "resend package not installed. Run: pip install resend"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to send test email: {str(e)}"}
