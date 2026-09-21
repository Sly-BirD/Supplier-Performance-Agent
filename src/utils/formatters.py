"""
Response formatters for scorecards, alerts, and narrative output.

Converts engine output (DimensionScore, CompositeScore, FiredAlert)
into user-facing text and structured JSON responses.
"""

from __future__ import annotations

from src.engines.scoring_engine import CompositeScore, DimensionScore
from src.engines.alert_engine import FiredAlert


def format_scorecard_text(
    supplier_name: str,
    composite: CompositeScore,
) -> str:
    """
    Format a scorecard as plain text for chat responses.

    Matches the format from About.md §9.1.
    """
    lines = [
        f"Supplier: {supplier_name}        "
        f"Tier: {composite.tier}   Trend: {composite.trend}",
        f"Composite Score: {composite.score:.0f}/100"
        + (f"  (was {composite.prior_score:.0f})" if composite.prior_score else ""),
        "",
    ]

    dimension_labels = {
        "quality": "Quality",
        "pricing": "Pricing",
        "delivery": "Delivery",
        "communication": "Communication",
        "reliability": "Reliability",
    }

    for dim_name, label in dimension_labels.items():
        dim_score = composite.dimension_scores.get(dim_name)
        if dim_score:
            detail_parts = []
            for m in dim_score.metrics:
                detail_parts.append(f"{m.description}")

            detail_str = "   ".join(detail_parts) if detail_parts else ""
            trend_marker = ""
            if dim_name == "delivery" and composite.trend == "↓":
                trend_marker = " ↓"

            lines.append(
                f"{label + ':':<18} {dim_score.score:.0f}/100{trend_marker}   {detail_str}"
            )
        else:
            lines.append(f"{label + ':':<18} —  (no data)")

    # Flags
    flags = []
    for dim_name, dim_score in composite.dimension_scores.items():
        if dim_score.score < 70:
            for m in dim_score.metrics:
                flags.append(
                    f"⚠ Flag: {dimension_labels.get(dim_name, dim_name)} "
                    f"score is {dim_score.score:.0f}/100. {m.description}"
                )

    if flags:
        lines.append("")
        lines.extend(flags)

    return "\n".join(lines)


def format_scorecard_json(
    supplier_id: str,
    supplier_name: str,
    composite: CompositeScore,
) -> dict:
    """Format a scorecard as structured JSON for API responses."""
    dimensions = {}
    for dim_name, dim_score in composite.dimension_scores.items():
        dimensions[dim_name] = {
            "score": dim_score.score,
            "data_points": dim_score.data_point_count,
            "metrics": [
                {
                    "name": m.metric_name,
                    "value": m.value,
                    "unit": m.unit,
                    "sample_size": m.sample_size,
                    "description": m.description,
                }
                for m in dim_score.metrics
            ],
        }

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "composite_score": composite.score,
        "tier": composite.tier,
        "trend": composite.trend,
        "prior_score": composite.prior_score,
        "dimensions": dimensions,
        "config_version": composite.config_version,
    }


def format_alert_text(alert: FiredAlert) -> str:
    """Format a fired alert as plain text for chat responses."""
    severity_emoji = {
        "low": "ℹ️",
        "medium": "⚠️",
        "high": "🔴",
        "critical": "🚨",
    }
    emoji = severity_emoji.get(alert.severity, "⚠️")

    lines = [
        f"{emoji} **{alert.title}**",
        f"Severity: {alert.severity.upper()}",
        "",
        alert.description,
    ]

    if alert.suggested_action:
        lines.extend(["", f"💡 Suggested action: {alert.suggested_action}"])

    return "\n".join(lines)


def format_alert_json(alert: FiredAlert) -> dict:
    """Format a fired alert as structured JSON for API responses."""
    return {
        "rule_type": alert.rule_type,
        "severity": alert.severity,
        "title": alert.title,
        "description": alert.description,
        "metric_value": alert.metric_value,
        "threshold_value": alert.threshold_value,
        "supplier_id": alert.supplier_id,
        "data_points": alert.data_points,
        "suggested_action": alert.suggested_action,
    }
