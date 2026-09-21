"""
Config store — CRUD operations on versioned, auditable configuration.

Every config change creates a new version. Old versions are retained so
the system can answer 'what settings were in use when this score was computed?'
and 'who approved this threshold change?'.

All operations are scoped by user_id for multi-tenant isolation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models import ConfigRecord, ConfigStatus


class ConfigStore:
    """Manages versioned configuration records in the database, scoped per tenant."""

    def __init__(self, session: AsyncSession, user_id: str = "dev-user"):
        self.session = session
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_active(self, config_type: str) -> ConfigRecord | None:
        """
        Get the latest approved config for a given type, scoped to the current user.

        Returns None if no config of this type has been approved yet —
        which means the agent needs to propose defaults.
        """
        stmt = (
            select(ConfigRecord)
            .where(
                ConfigRecord.user_id == self.user_id,
                ConfigRecord.config_type == config_type,
                ConfigRecord.status == ConfigStatus.APPROVED,
            )
            .order_by(desc(ConfigRecord.version))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending(self, config_type: str) -> ConfigRecord | None:
        """Get the latest proposed (not yet approved) config, if any."""
        stmt = (
            select(ConfigRecord)
            .where(
                ConfigRecord.user_id == self.user_id,
                ConfigRecord.config_type == config_type,
                ConfigRecord.status == ConfigStatus.PROPOSED,
            )
            .order_by(desc(ConfigRecord.version))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_history(
        self, config_type: str, limit: int = 20
    ) -> list[ConfigRecord]:
        """Get version history for a config type, newest first."""
        stmt = (
            select(ConfigRecord)
            .where(
                ConfigRecord.user_id == self.user_id,
                ConfigRecord.config_type == config_type,
            )
            .order_by(desc(ConfigRecord.version))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_version(
        self, config_type: str, version: int
    ) -> ConfigRecord | None:
        """Get a specific version of a config."""
        stmt = (
            select(ConfigRecord)
            .where(
                ConfigRecord.user_id == self.user_id,
                ConfigRecord.config_type == config_type,
                ConfigRecord.version == version,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def propose(self, config_type: str, payload: dict) -> ConfigRecord:
        """
        Create a new proposed config for the current user.

        This is what the agent calls when it wants to suggest settings.
        The config is NOT active until approved.
        """
        # Determine next version number
        latest = await self._get_latest(config_type)
        next_version = (latest.version + 1) if latest else 1

        record = ConfigRecord(
            user_id=self.user_id,
            config_type=config_type,
            payload=payload,
            status=ConfigStatus.PROPOSED,
            version=next_version,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def approve(
        self,
        config_id: str,
        approved_by: str = "user",
    ) -> ConfigRecord:
        """
        Approve a proposed config, making it the active version.

        Also marks any previously-active config as superseded.
        Validates that the config belongs to the current user.
        """
        # Get the record to approve
        stmt = select(ConfigRecord).where(
            ConfigRecord.id == config_id,
            ConfigRecord.user_id == self.user_id,
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            raise ValueError(f"Config record {config_id} not found")
        if record.status == ConfigStatus.APPROVED:
            raise ValueError(f"Config record {config_id} is already approved")

        # Mark previous active as superseded
        prev_active = await self.get_active(record.config_type)
        if prev_active:
            prev_active.superseded_by = record.id

        # Approve the new record
        record.status = ConfigStatus.APPROVED
        record.approved_at = datetime.now(timezone.utc)
        record.approved_by = approved_by

        await self.session.flush()
        return record

    async def update_and_propose(
        self,
        config_type: str,
        payload: dict,
    ) -> ConfigRecord:
        """
        Convenience: create a new version with updated payload.

        Used when the user wants to change settings — creates a new
        proposed version that can then be approved.
        """
        return await self.propose(config_type, payload)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _get_latest(self, config_type: str) -> ConfigRecord | None:
        """Get the latest config record regardless of status, for this user."""
        stmt = (
            select(ConfigRecord)
            .where(
                ConfigRecord.user_id == self.user_id,
                ConfigRecord.config_type == config_type,
            )
            .order_by(desc(ConfigRecord.version))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

