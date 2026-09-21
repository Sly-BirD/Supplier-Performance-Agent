"""
Alert Engine — deterministic threshold evaluation.

Evaluates alert rules against supplier data and fires alerts when thresholds
are breached. No LLM involvement — all checks are arithmetic comparisons
against user-approved AlertConfig thresholds.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.models import AlertConfig, AlertRule, AlertSeverityLevel
from src.data.models import (
    Alert as AlertModel,
    AlertRuleType,
    AlertSeverity,
    Dimension,
    TransactionRecord,
)
from src.engines.scoring_engine import CompositeScore


@dataclass
class FiredAlert:
    """An alert that has been triggered by a rule evaluation."""

    rule_type: str
    severity: str
    title: str
    description: str
    metric_value: float
    threshold_value: float
    supplier_id: str
    data_points: list[dict] = field(default_factory=list)
    suggested_action: str = ""


class AlertEngine:
    """
    Deterministic alert evaluation engine.

    Checks all enabled alert rules against current data and returns
    a list of fired alerts. The caller (agent orchestrator) is responsible
    for persisting and dispatching them.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def evaluate_all_rules(
        self,
        supplier_id: str,
        config: AlertConfig,
        composite_score: CompositeScore | None = None,
        prior_tier: str | None = None,
    ) -> list[FiredAlert]:
        """
        Evaluate all enabled alert rules for a supplier.

        Returns a list of FiredAlert objects for rules that triggered.
        """
        fired: list[FiredAlert] = []

        for rule in config.rules:
            if not rule.enabled:
                continue

            result = await self._evaluate_rule(
                supplier_id, rule, composite_score, prior_tier
            )
            if result:
                fired.append(result)

        return fired

    async def _evaluate_rule(
        self,
        supplier_id: str,
        rule: AlertRule,
        composite_score: CompositeScore | None,
        prior_tier: str | None,
    ) -> FiredAlert | None:
        """Dispatch to the appropriate rule evaluator."""
        evaluators = {
            "delay": self._check_delay,
            "price": self._check_price,
            "quality": self._check_quality,
            "communication": self._check_communication,
            "composite": self._check_composite,
        }

        evaluator = evaluators.get(rule.rule_type)
        if not evaluator:
            return None

        if rule.rule_type == "composite":
            return self._check_composite(
                supplier_id, rule, composite_score, prior_tier
            )

        return await evaluator(supplier_id, rule)

    # ------------------------------------------------------------------
    # Rule evaluators
    # ------------------------------------------------------------------

    async def _check_delay(
        self, supplier_id: str, rule: AlertRule
    ) -> FiredAlert | None:
        """
        Check: N or more late deliveries in rolling M-day window.

        A delivery is 'late' if its metric_value > 0 (days late).
        """
        window_days = rule.window_days or 30
        count_threshold = rule.count_threshold or int(rule.threshold_value)
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

        records = await self._get_dimension_records(
            supplier_id, Dimension.DELIVERY, cutoff
        )

        # Count late deliveries (metric_value > 0 = days late)
        late_records = [r for r in records if r.metric_value > 0]
        late_count = len(late_records)

        if late_count >= count_threshold:
            avg_days = (
                statistics.mean([r.metric_value for r in late_records])
                if late_records else 0
            )
            return FiredAlert(
                rule_type="delay",
                severity=rule.severity.value,
                title=f"Delivery Alert: {late_count} late deliveries in {window_days} days",
                description=(
                    f"{late_count} deliveries were late in the last {window_days} days "
                    f"(threshold: {count_threshold}). Average delay: {avg_days:.1f} days."
                ),
                metric_value=float(late_count),
                threshold_value=float(count_threshold),
                supplier_id=supplier_id,
                data_points=[
                    {
                        "date": r.record_date.isoformat(),
                        "days_late": r.metric_value,
                    }
                    for r in late_records[:10]
                ],
                suggested_action=(
                    "Review recent deliveries with this supplier. "
                    "Consider requesting a root cause analysis for the delays."
                ),
            )

        return None

    async def _check_price(
        self, supplier_id: str, rule: AlertRule
    ) -> FiredAlert | None:
        """Check: price increase > N% within the configured period."""
        window_days = rule.window_days or 90
        threshold_pct = rule.threshold_value
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

        records = await self._get_dimension_records(
            supplier_id, Dimension.PRICING, cutoff
        )

        price_records = [
            r for r in records
            if "price" in r.metric_name and "variance" not in r.metric_name
        ] or records

        if len(price_records) < 2:
            return None

        # Sort by date safely handling naive vs aware SQLite datetimes
        def _to_utc(dt: datetime) -> datetime:
            if dt is None:
                return datetime.now(timezone.utc)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        price_records.sort(key=lambda r: _to_utc(r.record_date))
        earliest_price = price_records[0].metric_value
        latest_price = price_records[-1].metric_value

        if earliest_price == 0:
            return None

        pct_change = ((latest_price - earliest_price) / abs(earliest_price)) * 100

        if pct_change > threshold_pct:
            return FiredAlert(
                rule_type="price",
                severity=rule.severity.value,
                title=f"Price Alert: {pct_change:+.1f}% increase detected",
                description=(
                    f"Price increased by {pct_change:.1f}% over the last {window_days} days "
                    f"(threshold: {threshold_pct}%). "
                    f"From {earliest_price:.2f} to {latest_price:.2f}."
                ),
                metric_value=round(pct_change, 2),
                threshold_value=threshold_pct,
                supplier_id=supplier_id,
                data_points=[
                    {"date": price_records[0].record_date.isoformat(), "price": earliest_price},
                    {"date": price_records[-1].record_date.isoformat(), "price": latest_price},
                ],
                suggested_action=(
                    "Review pricing terms with this supplier. "
                    "Compare against other suppliers in the same category."
                ),
            )

        return None

    async def _check_quality(
        self, supplier_id: str, rule: AlertRule
    ) -> FiredAlert | None:
        """
        Check: defect rate exceeds threshold OR statistical anomaly.

        Supports both flat threshold and std-dev-based anomaly detection.
        """
        window_days = rule.window_days or 90
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

        records = await self._get_dimension_records(
            supplier_id, Dimension.QUALITY, cutoff
        )

        defect_records = [r for r in records if "defect" in r.metric_name] or records

        if not defect_records:
            return None

        values = [r.metric_value for r in defect_records]
        current_rate = statistics.mean(values) * 100  # Convert to percentage

        # Std-dev anomaly detection
        if rule.std_dev_multiplier and len(values) > 2:
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values)
            latest_val = values[-1]

            if latest_val > mean_val + rule.std_dev_multiplier * std_val:
                return FiredAlert(
                    rule_type="quality",
                    severity=rule.severity.value,
                    title=f"Quality Anomaly: defect rate spike detected",
                    description=(
                        f"Latest defect rate ({latest_val*100:.2f}%) exceeds "
                        f"mean + {rule.std_dev_multiplier}σ "
                        f"(threshold: {(mean_val + rule.std_dev_multiplier * std_val)*100:.2f}%)."
                    ),
                    metric_value=round(latest_val * 100, 2),
                    threshold_value=round(
                        (mean_val + rule.std_dev_multiplier * std_val) * 100, 2
                    ),
                    supplier_id=supplier_id,
                    data_points=[
                        {"date": r.record_date.isoformat(), "defect_rate": r.metric_value}
                        for r in records[-5:]
                    ],
                    suggested_action=(
                        "Investigate the quality spike. "
                        "Request inspection reports and batch details."
                    ),
                )

        # Flat threshold check
        if rule.threshold_value > 0 and current_rate > rule.threshold_value:
            return FiredAlert(
                rule_type="quality",
                severity=rule.severity.value,
                title=f"Quality Alert: defect rate at {current_rate:.1f}%",
                description=(
                    f"Average defect rate ({current_rate:.1f}%) exceeds "
                    f"threshold ({rule.threshold_value}%)."
                ),
                metric_value=round(current_rate, 2),
                threshold_value=rule.threshold_value,
                supplier_id=supplier_id,
                suggested_action=(
                    "Review quality metrics with this supplier. "
                    "Consider requesting corrective action plan."
                ),
            )

        return None

    async def _check_communication(
        self, supplier_id: str, rule: AlertRule
    ) -> FiredAlert | None:
        """Check: response time exceeds SLA or issues unresolved > N days."""
        window_days = rule.window_days or 30
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

        records = await self._get_dimension_records(
            supplier_id, Dimension.COMMUNICATION, cutoff
        )

        if not records:
            return None

        values = [r.metric_value for r in records]
        avg_value = statistics.mean(values)

        if avg_value > rule.threshold_value:
            return FiredAlert(
                rule_type="communication",
                severity=rule.severity.value,
                title=f"Communication Alert: response metric at {avg_value:.1f}",
                description=(
                    f"Average communication metric ({avg_value:.1f}) exceeds "
                    f"threshold ({rule.threshold_value}). "
                    f"Based on {len(records)} data points."
                ),
                metric_value=round(avg_value, 2),
                threshold_value=rule.threshold_value,
                supplier_id=supplier_id,
                suggested_action=(
                    "Follow up on communication responsiveness. "
                    "Consider escalating unresolved issues."
                ),
            )

        return None

    def _check_composite(
        self,
        supplier_id: str,
        rule: AlertRule,
        composite_score: CompositeScore | None,
        prior_tier: str | None,
    ) -> FiredAlert | None:
        """Check: tier downgrade (e.g., Approved → Watch)."""
        if not composite_score or not prior_tier:
            return None

        if composite_score.tier != prior_tier:
            # Define tier order for comparison
            tier_order = {"Preferred": 4, "Approved": 3, "Watch": 2, "At-Risk": 1}
            old_rank = tier_order.get(prior_tier, 0)
            new_rank = tier_order.get(composite_score.tier, 0)

            if new_rank < old_rank:  # Downgrade
                return FiredAlert(
                    rule_type="composite",
                    severity=rule.severity.value,
                    title=f"Tier Downgrade: {prior_tier} → {composite_score.tier}",
                    description=(
                        f"Supplier tier changed from {prior_tier} to "
                        f"{composite_score.tier}. "
                        f"Composite score: {composite_score.score}/100."
                    ),
                    metric_value=composite_score.score,
                    threshold_value=0.0,
                    supplier_id=supplier_id,
                    suggested_action=(
                        "Review the supplier's overall performance. "
                        "Schedule a performance review meeting."
                    ),
                )

        return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def persist_alerts(
        self, alerts: list[FiredAlert]
    ) -> list[AlertModel]:
        """Save fired alerts to the database."""
        models: list[AlertModel] = []

        for alert in alerts:
            model = AlertModel(
                supplier_id=alert.supplier_id,
                rule_type=AlertRuleType(alert.rule_type),
                severity=AlertSeverity(alert.severity),
                title=alert.title,
                description=alert.description,
                metric_value=alert.metric_value,
                threshold_value=alert.threshold_value,
                data_points_json=alert.data_points,
                suggested_action=alert.suggested_action,
            )
            self.session.add(model)
            models.append(model)

        await self.session.flush()
        return models

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_dimension_records(
        self,
        supplier_id: str,
        dimension: Dimension,
        since: datetime,
    ) -> list[TransactionRecord]:
        """Fetch records for a supplier/dimension since a cutoff date."""
        stmt = (
            select(TransactionRecord)
            .where(
                and_(
                    TransactionRecord.supplier_id == supplier_id,
                    TransactionRecord.dimension == dimension,
                    TransactionRecord.record_date >= since,
                )
            )
            .order_by(TransactionRecord.record_date)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
