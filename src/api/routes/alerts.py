"""
Alerts route — alert feed and management.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_user_id
from src.data.models import Alert, Supplier

router = APIRouter()


class AlertResponse(BaseModel):
    """Alert data."""
    id: str
    supplier_id: str
    rule_type: str
    severity: str
    title: str
    description: str | None = None
    metric_value: float
    threshold_value: float
    suggested_action: str | None = None
    acknowledged: bool
    fired_at: str


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    supplier_id: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    acknowledged: bool | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """List alerts scoped to the authenticated user's suppliers."""
    # Join alerts to suppliers to enforce tenant isolation
    stmt = (
        select(Alert)
        .join(Supplier, Alert.supplier_id == Supplier.id)
        .where(Supplier.user_id == user_id)
        .order_by(desc(Alert.fired_at))
        .limit(limit)
    )

    if supplier_id:
        stmt = stmt.where(Alert.supplier_id == supplier_id)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if acknowledged is not None:
        stmt = stmt.where(Alert.acknowledged == acknowledged)

    result = await db.execute(stmt)
    alerts = result.scalars().all()

    return [
        AlertResponse(
            id=a.id,
            supplier_id=a.supplier_id,
            rule_type=a.rule_type.value,
            severity=a.severity.value,
            title=a.title,
            description=a.description,
            metric_value=a.metric_value,
            threshold_value=a.threshold_value,
            suggested_action=a.suggested_action,
            acknowledged=a.acknowledged,
            fired_at=a.fired_at.isoformat() if a.fired_at else "",
        )
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Mark an alert as acknowledged, verifying ownership through supplier."""
    from datetime import datetime, timezone

    # Verify alert belongs to this user's supplier
    stmt = (
        select(Alert)
        .join(Supplier, Alert.supplier_id == Supplier.id)
        .where(Alert.id == alert_id, Supplier.user_id == user_id)
    )
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.acknowledged = True
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.flush()

    return {"status": "acknowledged", "alert_id": alert_id}

