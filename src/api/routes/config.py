"""
Config route — view and manage configuration settings.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_user_id
from src.config.store import ConfigStore

router = APIRouter()


class ConfigResponse(BaseModel):
    """Configuration data."""
    id: str
    config_type: str
    payload: dict
    status: str
    version: int
    proposed_at: str | None = None
    approved_at: str | None = None
    approved_by: str | None = None


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration."""
    config_type: str
    payload: dict


class ApproveRequest(BaseModel):
    """Request to approve a pending configuration."""
    config_id: str
    approved_by: str = "user"


@router.get("/config/{config_type}", response_model=ConfigResponse | None)
async def get_config(
    config_type: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Get the active (approved) configuration for a given type, scoped to user."""
    store = ConfigStore(db, user_id=user_id)
    record = await store.get_active(config_type)

    if not record:
        return None

    return ConfigResponse(
        id=record.id,
        config_type=record.config_type,
        payload=record.payload,
        status=record.status.value,
        version=record.version,
        proposed_at=record.proposed_at.isoformat() if record.proposed_at else None,
        approved_at=record.approved_at.isoformat() if record.approved_at else None,
        approved_by=record.approved_by,
    )


@router.get("/config/{config_type}/history", response_model=list[ConfigResponse])
async def get_config_history(
    config_type: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Get version history for a configuration type, scoped to user."""
    store = ConfigStore(db, user_id=user_id)
    records = await store.get_history(config_type, limit=limit)

    return [
        ConfigResponse(
            id=r.id,
            config_type=r.config_type,
            payload=r.payload,
            status=r.status.value,
            version=r.version,
            proposed_at=r.proposed_at.isoformat() if r.proposed_at else None,
            approved_at=r.approved_at.isoformat() if r.approved_at else None,
            approved_by=r.approved_by,
        )
        for r in records
    ]


@router.put("/config", response_model=ConfigResponse)
async def update_config(
    request: ConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Propose a config update for the current user.
    Creates a new version with status='proposed'.
    Must be approved via POST /config/approve before it takes effect.
    """
    store = ConfigStore(db, user_id=user_id)
    record = await store.propose(request.config_type, request.payload)

    return ConfigResponse(
        id=record.id,
        config_type=record.config_type,
        payload=record.payload,
        status=record.status.value,
        version=record.version,
        proposed_at=record.proposed_at.isoformat() if record.proposed_at else None,
    )


@router.post("/config/approve", response_model=ConfigResponse)
async def approve_config(
    request: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Approve a pending configuration, making it active for this user."""
    store = ConfigStore(db, user_id=user_id)

    try:
        record = await store.approve(request.config_id, request.approved_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ConfigResponse(
        id=record.id,
        config_type=record.config_type,
        payload=record.payload,
        status=record.status.value,
        version=record.version,
        proposed_at=record.proposed_at.isoformat() if record.proposed_at else None,
        approved_at=record.approved_at.isoformat() if record.approved_at else None,
        approved_by=record.approved_by,
    )

