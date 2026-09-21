"""
Proposed default values for all configurable settings.

These are NEVER auto-applied. The agent surfaces them to the user as
starting suggestions and waits for explicit approval before using them.

Each default includes a plain-language rationale so the agent can explain
*why* it's suggesting this value.
"""

from __future__ import annotations

from src.config.models import (
    AlertConfig,
    AlertRule,
    AlertChannel,
    AlertSeverityLevel,
    DimensionWeights,
    OnTimeDefinition,
    OnTimeMethod,
    PricingBenchmark,
    ScoringConfig,
    TierBoundary,
)


# ---------------------------------------------------------------------------
# Scoring defaults
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS = DimensionWeights(
    quality=25,
    pricing=20,
    delivery=25,
    communication=15,
    reliability=15,
)

DEFAULT_ON_TIME = OnTimeDefinition(
    method=OnTimeMethod.GRACE_WINDOW,
    grace_days=2,
)

DEFAULT_TIERS = [
    TierBoundary(name="Preferred", min_score=90, color="#22c55e"),
    TierBoundary(name="Approved", min_score=75, color="#3b82f6"),
    TierBoundary(name="Watch", min_score=60, color="#f59e0b"),
    TierBoundary(name="At-Risk", min_score=0, color="#ef4444"),
]

DEFAULT_SCORING_CONFIG = ScoringConfig(
    weights=DEFAULT_WEIGHTS,
    on_time=DEFAULT_ON_TIME,
    pricing_benchmark=PricingBenchmark.CATEGORY_AVERAGE,
    current_window_days=90,
    trend_window_days=365,
    retention_depth_days=730,
    tiers=DEFAULT_TIERS,
)


# ---------------------------------------------------------------------------
# Alert defaults
# ---------------------------------------------------------------------------

DEFAULT_ALERT_RULES = [
    AlertRule(
        rule_type="delay",
        description="Alert when N or more deliveries are late in a rolling M-day window",
        threshold_value=3,  # N late deliveries
        window_days=30,     # in last M days
        count_threshold=3,
        severity=AlertSeverityLevel.HIGH,
    ),
    AlertRule(
        rule_type="price",
        description="Alert when price increases by more than N% within a period",
        threshold_value=8.0,  # >8% increase
        window_days=90,
        severity=AlertSeverityLevel.MEDIUM,
    ),
    AlertRule(
        rule_type="quality",
        description="Alert when defect rate exceeds a set threshold",
        threshold_value=5.0,  # >5% defect rate
        severity=AlertSeverityLevel.HIGH,
    ),
    AlertRule(
        rule_type="quality",
        description="Alert on statistical anomaly in defect rate (> mean + k*stddev)",
        threshold_value=0.0,  # Placeholder — anomaly is std-dev based
        std_dev_multiplier=2.0,
        window_days=90,
        severity=AlertSeverityLevel.MEDIUM,
    ),
    AlertRule(
        rule_type="communication",
        description="Alert when average response time exceeds SLA value",
        threshold_value=24.0,  # >24 hours avg response
        severity=AlertSeverityLevel.MEDIUM,
    ),
    AlertRule(
        rule_type="communication",
        description="Alert when an issue remains unresolved for more than N days",
        threshold_value=7.0,  # >7 days unresolved
        severity=AlertSeverityLevel.HIGH,
    ),
    AlertRule(
        rule_type="composite",
        description="Alert on tier downgrade (e.g., Approved → Watch)",
        threshold_value=0.0,  # N/A — triggered by tier change
        severity=AlertSeverityLevel.CRITICAL,
    ),
]

DEFAULT_ALERT_CONFIG = AlertConfig(
    rules=DEFAULT_ALERT_RULES,
    delivery_channels=[AlertChannel.IN_APP, AlertChannel.EMAIL],
    email_recipients=[],
    digest_frequency_hours=None,  # Send immediately by default
)


# ---------------------------------------------------------------------------
# Rationale strings (for the agent to explain its proposals)
# ---------------------------------------------------------------------------

RATIONALE = {
    "weights": (
        "Quality and Delivery are weighted highest (25% each) because defects and "
        "delays have the most direct operational impact. Pricing is at 20% since cost "
        "matters but is less volatile short-term. Communication and Reliability are at "
        "15% each — important for long-term relationships but typically secondary to "
        "quality and delivery for day-to-day decisions."
    ),
    "on_time_grace": (
        "A ±2-day grace window is common in most industries — it accounts for "
        "weekends, shipping variability, and minor logistics delays without "
        "penalizing suppliers unfairly. Set to 0 if you need exact-date adherence."
    ),
    "pricing_benchmark": (
        "Category average is the default benchmark because it compares apples to "
        "apples — each supplier is measured against peers in the same category. "
        "Switch to 'contract terms' if you have negotiated prices, or 'historical' "
        "to track a supplier's own price drift."
    ),
    "current_window": (
        "90 days gives a meaningful recent snapshot without being too noisy "
        "(shorter windows are volatile) or too stale (longer windows mask trends)."
    ),
    "trend_window": (
        "365 days for trend comparison provides a full year of context, "
        "accounting for seasonal patterns."
    ),
    "tiers": (
        "Four tiers (Preferred ≥90, Approved ≥75, Watch ≥60, At-Risk <60) "
        "provide clear differentiation. Adjust the boundaries and labels to "
        "match your organization's terminology."
    ),
}
