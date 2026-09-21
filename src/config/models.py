"""
Pydantic V2 models for all user-configurable settings.

Every setting in this module is user-owned: the agent proposes defaults
(see defaults.py), but nothing is applied until the user explicitly approves.

These models serve as both runtime validation AND the schema documentation
for the Config UI.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OnTimeMethod(str, Enum):
    """How 'on time' is defined for delivery scoring."""
    EXACT = "exact"  # Must arrive on or before the promised date
    GRACE_WINDOW = "grace_window"  # Allowed ±N days around the promised date


class PricingBenchmark(str, Enum):
    """What to compare a supplier's price against."""
    CATEGORY_AVERAGE = "category_average"  # Avg price across same-category suppliers
    CONTRACT_TERMS = "contract_terms"  # Agreed contract price
    HISTORICAL = "historical"  # Supplier's own past prices


class AlertChannel(str, Enum):
    """Where alerts are delivered."""
    IN_APP = "in_app"
    EMAIL = "email"


class AlertSeverityLevel(str, Enum):
    """Alert severity classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Config components
# ---------------------------------------------------------------------------

class DimensionWeights(BaseModel):
    """
    Weights for each scoring dimension. Must sum to 100.

    These are the user's judgment call — the agent proposes starting values
    but never assumes them.
    """

    quality: Annotated[float, Field(ge=0, le=100, description="Weight for quality dimension")]
    pricing: Annotated[float, Field(ge=0, le=100, description="Weight for pricing dimension")]
    delivery: Annotated[float, Field(ge=0, le=100, description="Weight for delivery dimension")]
    communication: Annotated[
        float, Field(ge=0, le=100, description="Weight for communication dimension")
    ]
    reliability: Annotated[
        float, Field(ge=0, le=100, description="Weight for reliability dimension")
    ]

    @model_validator(mode="after")
    def weights_must_sum_to_100(self) -> DimensionWeights:
        total = (
            self.quality + self.pricing + self.delivery
            + self.communication + self.reliability
        )
        if abs(total - 100.0) > 0.01:
            raise ValueError(
                f"Dimension weights must sum to 100, got {total:.2f}. "
                f"Current: quality={self.quality}, pricing={self.pricing}, "
                f"delivery={self.delivery}, communication={self.communication}, "
                f"reliability={self.reliability}"
            )
        return self


class OnTimeDefinition(BaseModel):
    """Defines what counts as 'on time' for delivery scoring."""

    method: OnTimeMethod = OnTimeMethod.GRACE_WINDOW
    grace_days: Annotated[
        int, Field(ge=0, le=30, description="±N days grace window (0 = exact match)")
    ] = 2


class TierBoundary(BaseModel):
    """A single tier/grade boundary (e.g., 'Preferred' >= 90)."""

    name: str = Field(description="Tier label, e.g., 'Preferred', 'Approved', 'Watch', 'At-Risk'")
    min_score: Annotated[
        float, Field(ge=0, le=100, description="Minimum composite score for this tier")
    ]
    color: str | None = Field(
        default=None, description="Optional display color, e.g., '#22c55e'"
    )


class ScoringConfig(BaseModel):
    """
    Complete scoring configuration — all user-owned settings.

    Controls how supplier performance is measured and graded.
    """

    weights: DimensionWeights
    on_time: OnTimeDefinition = Field(default_factory=OnTimeDefinition)
    pricing_benchmark: PricingBenchmark = PricingBenchmark.CATEGORY_AVERAGE
    current_window_days: Annotated[
        int, Field(gt=0, le=730, description="Days for 'current period' scoring")
    ] = 90
    trend_window_days: Annotated[
        int, Field(gt=0, le=1825, description="Days for trend comparison")
    ] = 365
    retention_depth_days: Annotated[
        int, Field(gt=0, description="How far back to keep data (days)")
    ] = 730
    tiers: list[TierBoundary] = Field(
        default_factory=lambda: [
            TierBoundary(name="Preferred", min_score=90, color="#22c55e"),
            TierBoundary(name="Approved", min_score=75, color="#3b82f6"),
            TierBoundary(name="Watch", min_score=60, color="#f59e0b"),
            TierBoundary(name="At-Risk", min_score=0, color="#ef4444"),
        ],
        description="Tier boundaries, ordered highest-first",
    )

    @model_validator(mode="after")
    def tiers_must_be_ordered(self) -> ScoringConfig:
        scores = [t.min_score for t in self.tiers]
        if scores != sorted(scores, reverse=True):
            raise ValueError("Tiers must be ordered from highest min_score to lowest")
        return self


class AlertRule(BaseModel):
    """A single alert rule template with user-set thresholds."""

    rule_type: str = Field(description="delay | price | quality | communication | composite")
    enabled: bool = True
    description: str = Field(description="Human-readable rule description")
    threshold_value: float = Field(description="The numeric threshold that triggers the alert")
    window_days: int | None = Field(
        default=None, description="Rolling window in days (if applicable)"
    )
    count_threshold: int | None = Field(
        default=None, description="Count threshold (e.g., N late deliveries)"
    )
    severity: AlertSeverityLevel = AlertSeverityLevel.MEDIUM
    std_dev_multiplier: float | None = Field(
        default=None,
        description="For anomaly detection: alert if metric > mean + k*stddev",
    )


class AlertConfig(BaseModel):
    """Complete alerting configuration — all user-owned settings."""

    rules: list[AlertRule] = Field(default_factory=list)
    delivery_channels: list[AlertChannel] = Field(
        default_factory=lambda: [AlertChannel.IN_APP, AlertChannel.EMAIL]
    )
    email_recipients: list[str] = Field(default_factory=list)
    digest_frequency_hours: int | None = Field(
        default=None,
        description="If set, batch alerts into digests every N hours instead of sending immediately",
    )
