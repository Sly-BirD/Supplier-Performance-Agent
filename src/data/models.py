"""
ORM models for the Supplier Performance Agent.

Core tables:
- Supplier          — Master supplier record
- DataSource        — Tracks each ingested file or connector
- SchemaMapping     — Approved column→dimension mapping per source
- TransactionRecord — Normalized row of supplier data
- ScoreSnapshot     — Point-in-time computed score per supplier/dimension
- Alert             — Fired alert instance
- ConfigRecord      — Versioned, auditable configuration entries
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Dimension(str, enum.Enum):
    """The five tracked performance dimensions."""
    QUALITY = "quality"
    PRICING = "pricing"
    DELIVERY = "delivery"
    COMMUNICATION = "communication"
    RELIABILITY = "reliability"


class SourceType(str, enum.Enum):
    """Types of data sources the agent can ingest."""
    CSV = "csv"
    EXCEL = "excel"
    ERP = "erp"
    GOOGLE_SHEETS = "google_sheets"
    EMAIL = "email"
    TICKETING = "ticketing"


class MappingStatus(str, enum.Enum):
    """Status of a schema mapping."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class ConfigStatus(str, enum.Enum):
    """Status of a configuration record."""
    PROPOSED = "proposed"
    APPROVED = "approved"


class AlertSeverity(str, enum.Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertRuleType(str, enum.Enum):
    """Types of alert rules."""
    DELAY = "delay"
    PRICE = "price"
    QUALITY = "quality"
    COMMUNICATION = "communication"
    COMPOSITE = "composite"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Supplier(Base):
    """Master supplier record."""

    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
        comment="Clerk user ID — scopes this supplier to a single tenant",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    transaction_records: Mapped[list[TransactionRecord]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan"
    )
    score_snapshots: Mapped[list[ScoreSnapshot]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan"
    )
    alerts: Mapped[list[Alert]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Supplier(id={self.id!r}, name={self.name!r})>"


class DataSource(Base):
    """Tracks each ingested file or connector instance."""

    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
        comment="Clerk user ID — scopes this data source to a single tenant",
    )
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_signature: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True,
        comment="Hash of column headers+types for cache matching",
    )
    schema_mapping_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("schema_mappings.id"), nullable=True
    )
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    schema_mapping: Mapped[SchemaMapping | None] = relationship(back_populates="data_sources")
    transaction_records: Mapped[list[TransactionRecord]] = relationship(
        back_populates="data_source", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DataSource(id={self.id!r}, type={self.source_type!r})>"


class SchemaMapping(Base):
    """
    Approved column→dimension mapping for a data source.

    Each mapping is versioned. When a source's structure changes, a new
    mapping is proposed and the old one is retained for audit.
    """

    __tablename__ = "schema_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
        comment="Clerk user ID — scopes this schema mapping to a single tenant",
    )
    source_signature: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        comment="Hash of the source's column structure",
    )
    mapping_json: Mapped[dict] = mapped_column(
        JSON, nullable=False,
        comment="Column-name → {dimension, metric_name, data_type} mapping",
    )
    column_descriptions: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Plain-language descriptions of what the agent inferred per column",
    )
    status: Mapped[MappingStatus] = mapped_column(
        Enum(MappingStatus), default=MappingStatus.PROPOSED
    )
    proposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    data_sources: Mapped[list[DataSource]] = relationship(back_populates="schema_mapping")

    def __repr__(self) -> str:
        return (
            f"<SchemaMapping(id={self.id!r}, status={self.status!r}, "
            f"version={self.version})>"
        )


class TransactionRecord(Base):
    """
    Normalized row of supplier performance data.

    Each row represents a single metric observation (e.g., one delivery,
    one quality inspection, one price point) after schema-mapping has been
    applied to the raw source data.
    """

    __tablename__ = "transaction_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    supplier_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("suppliers.id"), nullable=False, index=True
    )
    data_source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("data_sources.id"), nullable=False
    )
    dimension: Mapped[Dimension] = mapped_column(Enum(Dimension), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="e.g. 'defect_rate', 'on_time_delivery', 'price_variance'",
    )
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    record_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    raw_row_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Original row data for auditability",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    supplier: Mapped[Supplier] = relationship(back_populates="transaction_records")
    data_source: Mapped[DataSource] = relationship(back_populates="transaction_records")

    # Indexes
    __table_args__ = (
        Index("ix_transaction_records_sup_dim_date", "supplier_id", "dimension", "record_date"),
        Index("ix_transaction_records_sup_date", "supplier_id", "record_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<TransactionRecord(supplier={self.supplier_id!r}, "
            f"dim={self.dimension!r}, metric={self.metric_name!r})>"
        )


class ScoreSnapshot(Base):
    """
    Point-in-time computed score for a supplier.

    Stores both per-dimension scores and the weighted composite.
    Immutable once computed — new scoring runs create new snapshots.
    """

    __tablename__ = "score_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    supplier_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("suppliers.id"), nullable=False, index=True
    )
    dimension: Mapped[Dimension | None] = mapped_column(
        Enum(Dimension), nullable=True,
        comment="NULL for composite scores",
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    metric_details: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Breakdown of how the score was computed",
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tier: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="Tier label (Preferred/Approved/Watch/At-Risk) — only on composites",
    )
    trend: Mapped[str | None] = mapped_column(
        String(10), nullable=True,
        comment="↑, ↓, or flat — vs. prior period",
    )
    config_version: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Which config version was used to compute this score",
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    supplier: Mapped[Supplier] = relationship(back_populates="score_snapshots")

    # Indexes
    __table_args__ = (
        Index("ix_score_snapshots_sup_dim_computed", "supplier_id", "dimension", "computed_at"),
    )

    def __repr__(self) -> str:
        dim = self.dimension or "composite"
        return f"<ScoreSnapshot(supplier={self.supplier_id!r}, dim={dim}, score={self.score})>"


class Alert(Base):
    """
    A fired alert instance.

    Created when a threshold is breached. Includes the metric value,
    the threshold, and the supporting data points for auditability.
    """

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    supplier_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("suppliers.id"), nullable=False, index=True
    )
    rule_type: Mapped[AlertRuleType] = mapped_column(Enum(AlertRuleType), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    data_points_json: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Supporting data rows that triggered this alert",
    )
    suggested_action: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Agent's recommended next step (user acts, agent doesn't)",
    )
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    fired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    supplier: Mapped[Supplier] = relationship(back_populates="alerts")

    # Indexes
    __table_args__ = (
        Index("ix_alerts_ack_fired", "acknowledged", "fired_at"),
        Index("ix_alerts_sup_fired", "supplier_id", "fired_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Alert(supplier={self.supplier_id!r}, rule={self.rule_type!r}, "
            f"severity={self.severity!r})>"
        )


class ConfigRecord(Base):
    """
    Versioned, auditable configuration record.

    Every config change (weights, thresholds, time windows, tier boundaries)
    creates a new version. Old versions are retained for audit trail.
    """

    __tablename__ = "config_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
        comment="Clerk user ID — scopes this config to a single tenant",
    )
    config_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="e.g. 'scoring', 'alerting', 'schema_mapping'",
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[ConfigStatus] = mapped_column(
        Enum(ConfigStatus), default=ConfigStatus.PROPOSED
    )
    proposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    superseded_by: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
        comment="ID of the config record that replaced this one",
    )

    def __repr__(self) -> str:
        return (
            f"<ConfigRecord(type={self.config_type!r}, status={self.status!r}, "
            f"version={self.version})>"
        )
