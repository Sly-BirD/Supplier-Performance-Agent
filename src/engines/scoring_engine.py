"""
Scoring Engine — 100% deterministic, no LLM involvement.

Computes per-dimension scores (0–100) and a weighted composite for each
supplier using data from TransactionRecords and the user-approved ScoringConfig.

Every calculation is auditable: the engine returns both the score and the
metric details that produced it.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.models import ScoringConfig, PricingBenchmark
from src.data.models import (
    Dimension,
    ScoreSnapshot,
    Supplier,
    TransactionRecord,
)


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

@dataclass
class MetricDetail:
    """Breakdown of a single metric computation."""

    metric_name: str
    value: float
    unit: str  # e.g., "%", "days", "hours"
    sample_size: int  # Number of data points used
    description: str  # Human-readable explanation


@dataclass
class DimensionScore:
    """Score for a single dimension (0–100) with supporting details."""

    dimension: Dimension
    score: float
    metrics: list[MetricDetail] = field(default_factory=list)
    data_point_count: int = 0
    window_start: datetime | None = None
    window_end: datetime | None = None


@dataclass
class CompositeScore:
    """Weighted composite of all scored dimensions."""

    score: float  # 0–100
    tier: str  # e.g., "Preferred", "Approved", "Watch", "At-Risk"
    trend: str  # "↑", "↓", "flat"
    dimension_scores: dict[str, DimensionScore] = field(default_factory=dict)
    prior_score: float | None = None
    config_version: int | None = None


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ScoringEngine:
    """
    Deterministic scoring engine.

    All scores are computed from TransactionRecords using arithmetic
    formulas and the user-approved ScoringConfig. No LLM calls.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def score_supplier(
        self,
        supplier_id: str,
        config: ScoringConfig,
        config_version: int | None = None,
    ) -> CompositeScore:
        """
        Compute the full scorecard for a supplier.

        Returns a CompositeScore with per-dimension breakdowns, tier,
        and trend vs. prior period.
        """
        now = datetime.now(timezone.utc)
        window_end = now
        window_start = now - timedelta(days=config.current_window_days)
        prior_start = window_start - timedelta(days=config.current_window_days)

        # Optimization: Fetch all records for both current and prior windows in a single DB query
        stmt = (
            select(TransactionRecord)
            .where(
                and_(
                    TransactionRecord.supplier_id == supplier_id,
                    TransactionRecord.record_date >= prior_start,
                    TransactionRecord.record_date <= window_end,
                )
            )
            .order_by(TransactionRecord.record_date)
        )
        result = await self.session.execute(stmt)
        all_records = list(result.scalars().all())

        # Partition records in memory by window and dimension
        current_records: dict[Dimension, list[TransactionRecord]] = {d: [] for d in Dimension}
        prior_records: dict[Dimension, list[TransactionRecord]] = {d: [] for d in Dimension}
        has_prior_records = False

        for rec in all_records:
            if rec.record_date >= window_start:
                if rec.dimension in current_records:
                    current_records[rec.dimension].append(rec)
            else:
                has_prior_records = True
                if rec.dimension in prior_records:
                    prior_records[rec.dimension].append(rec)

        # Score each dimension
        dim_scores: dict[str, DimensionScore] = {}
        available_weight = 0.0

        for dimension in Dimension:
            records = current_records[dimension]
            if not records:
                # No data for this dimension — skip it (don't guess)
                continue

            score = self._compute_dimension_score(dimension, records, config)
            score.window_start = window_start
            score.window_end = window_end
            dim_scores[dimension.value] = score

            weight = self._get_weight(dimension, config)
            available_weight += weight

        # Compute weighted composite (re-normalize weights if some dimensions missing)
        composite_value = 0.0
        if available_weight > 0:
            for dim_name, dim_score in dim_scores.items():
                dimension = Dimension(dim_name)
                weight = self._get_weight(dimension, config)
                normalized_weight = weight / available_weight
                composite_value += dim_score.score * normalized_weight

        composite_value = round(min(100.0, max(0.0, composite_value)), 1)

        # Determine tier
        tier = self._assign_tier(composite_value, config)

        # Compute trend vs. prior period
        trend = "flat"
        prior_score = None

        if has_prior_records:
            prior_composite = self._compute_prior_composite_from_partitioned(
                prior_records, config
            )
            if prior_composite is not None:
                prior_score = prior_composite
                diff = composite_value - prior_composite
                if diff > 2.0:
                    trend = "↑"
                elif diff < -2.0:
                    trend = "↓"

        return CompositeScore(
            score=composite_value,
            tier=tier,
            trend=trend,
            dimension_scores=dim_scores,
            prior_score=prior_score,
            config_version=config_version,
        )

    # ------------------------------------------------------------------
    # Dimension scoring
    # ------------------------------------------------------------------

    def _compute_dimension_score(
        self,
        dimension: Dimension,
        records: list[TransactionRecord],
        config: ScoringConfig,
    ) -> DimensionScore:
        """Route to the appropriate dimension-specific scoring method."""
        scorers = {
            Dimension.QUALITY: self._score_quality,
            Dimension.PRICING: self._score_pricing,
            Dimension.DELIVERY: self._score_delivery,
            Dimension.COMMUNICATION: self._score_communication,
            Dimension.RELIABILITY: self._score_reliability,
        }
        return scorers[dimension](records, config)

    def _score_quality(
        self, records: list[TransactionRecord], config: ScoringConfig
    ) -> DimensionScore:
        """
        Quality score based on defect rate.

        Score = (1 - defect_rate) * 100, capped at [0, 100].
        """
        defect_values = [r.metric_value for r in records if "defect" in r.metric_name]
        inspection_values = [r.metric_value for r in records if "inspection" in r.metric_name or "pass" in r.metric_name]

        metrics: list[MetricDetail] = []

        if defect_values:
            avg_defect_rate = statistics.mean(defect_values)
            score = max(0.0, min(100.0, (1 - avg_defect_rate) * 100))
            metrics.append(MetricDetail(
                metric_name="defect_rate",
                value=round(avg_defect_rate * 100, 2),
                unit="%",
                sample_size=len(defect_values),
                description=f"Average defect rate: {avg_defect_rate*100:.2f}%",
            ))
        elif inspection_values:
            avg_pass_rate = statistics.mean(inspection_values)
            score = max(0.0, min(100.0, avg_pass_rate * 100))
            metrics.append(MetricDetail(
                metric_name="inspection_pass_rate",
                value=round(avg_pass_rate * 100, 2),
                unit="%",
                sample_size=len(inspection_values),
                description=f"Average inspection pass rate: {avg_pass_rate*100:.2f}%",
            ))
        else:
            # Use raw metric values as a generic quality signal
            avg_val = statistics.mean([r.metric_value for r in records])
            score = max(0.0, min(100.0, avg_val))
            metrics.append(MetricDetail(
                metric_name="quality_generic",
                value=round(avg_val, 2),
                unit="score",
                sample_size=len(records),
                description=f"Average quality metric: {avg_val:.2f}",
            ))

        return DimensionScore(
            dimension=Dimension.QUALITY,
            score=round(score, 1),
            metrics=metrics,
            data_point_count=len(records),
        )

    def _score_pricing(
        self, records: list[TransactionRecord], config: ScoringConfig
    ) -> DimensionScore:
        """
        Pricing score based on variance from benchmark.

        Lower variance = higher score.
        Score = max(0, 100 - |avg_variance| * 5)
        """
        variance_values = [
            r.metric_value for r in records
            if "variance" in r.metric_name
        ]

        if not variance_values and records:
            prices = [r.metric_value for r in records if "price" in r.metric_name]
            if len(prices) > 1 and prices[0] > 0:
                variance_values = [((p - prices[0]) / prices[0]) * 100 for p in prices]
            elif prices:
                variance_values = [0.0]
            else:
                variance_values = [r.metric_value for r in records]

        avg_variance = statistics.mean(variance_values) if variance_values else 0.0

        # Higher variance = lower score; scale so ±20% variance = 0 score
        score = max(0.0, min(100.0, 100 - abs(avg_variance) * 5))

        metrics = [
            MetricDetail(
                metric_name="price_variance",
                value=round(avg_variance, 2),
                unit="%",
                sample_size=len(variance_values),
                description=f"Average price variance: {avg_variance:+.2f}% vs. benchmark",
            ),
        ]

        # Price stability (lower std dev = better)
        if len(variance_values) > 1:
            stability = statistics.stdev(variance_values)
            metrics.append(MetricDetail(
                metric_name="price_stability",
                value=round(stability, 2),
                unit="σ",
                sample_size=len(variance_values),
                description=f"Price stability (std dev): {stability:.2f}",
            ))

        return DimensionScore(
            dimension=Dimension.PRICING,
            score=round(score, 1),
            metrics=metrics,
            data_point_count=len(records),
        )

    def _score_delivery(
        self, records: list[TransactionRecord], config: ScoringConfig
    ) -> DimensionScore:
        """
        Delivery score based on on-time rate.

        A delivery is 'on time' if days_late <= grace_days (from config).
        Score = on_time_rate * 100.
        """
        grace = config.on_time.grace_days

        on_time_values = [
            r.metric_value for r in records
            if "on_time" in r.metric_name or "late" in r.metric_name or "delay" in r.metric_name
        ]

        if not on_time_values:
            on_time_values = [r.metric_value for r in records]

        # Interpret: if metric is 'days_late', on_time = (days_late <= grace)
        late_records = [v for v in on_time_values if v > grace]
        on_time_count = len(on_time_values) - len(late_records)
        on_time_rate = on_time_count / len(on_time_values) if on_time_values else 1.0

        score = on_time_rate * 100
        avg_days_late = statistics.mean(on_time_values) if on_time_values else 0.0

        metrics = [
            MetricDetail(
                metric_name="on_time_rate",
                value=round(on_time_rate * 100, 1),
                unit="%",
                sample_size=len(on_time_values),
                description=(
                    f"On-time delivery rate: {on_time_rate*100:.1f}% "
                    f"({on_time_count}/{len(on_time_values)} deliveries, "
                    f"grace window ±{grace} days)"
                ),
            ),
            MetricDetail(
                metric_name="avg_days_late",
                value=round(avg_days_late, 1),
                unit="days",
                sample_size=len(on_time_values),
                description=f"Average days late: {avg_days_late:.1f}",
            ),
        ]

        return DimensionScore(
            dimension=Dimension.DELIVERY,
            score=round(max(0.0, min(100.0, score)), 1),
            metrics=metrics,
            data_point_count=len(records),
        )

    def _score_communication(
        self, records: list[TransactionRecord], config: ScoringConfig
    ) -> DimensionScore:
        """
        Communication score based on response time and resolution rate.

        Faster response + higher resolution = higher score.
        """
        response_times = [
            r.metric_value for r in records
            if "response" in r.metric_name or "reply" in r.metric_name
        ]
        resolution_values = [
            r.metric_value for r in records
            if "resolution" in r.metric_name or "resolved" in r.metric_name
        ]

        metrics: list[MetricDetail] = []
        sub_scores: list[float] = []

        if response_times:
            avg_response = statistics.mean(response_times)
            # Score: 100 if < 1h, 0 if > 48h, linear in between
            rt_score = max(0.0, min(100.0, 100 - (avg_response - 1) * (100 / 47)))
            sub_scores.append(rt_score)
            metrics.append(MetricDetail(
                metric_name="avg_response_time",
                value=round(avg_response, 1),
                unit="hours",
                sample_size=len(response_times),
                description=f"Average response time: {avg_response:.1f}h",
            ))

        if resolution_values:
            avg_resolution = statistics.mean(resolution_values)
            res_score = avg_resolution * 100  # Assuming rate is 0.0–1.0
            sub_scores.append(min(100.0, res_score))
            metrics.append(MetricDetail(
                metric_name="resolution_rate",
                value=round(avg_resolution * 100, 1),
                unit="%",
                sample_size=len(resolution_values),
                description=f"Resolution rate: {avg_resolution*100:.1f}%",
            ))

        if not sub_scores:
            # Fallback: use raw values
            all_vals = [r.metric_value for r in records]
            score = statistics.mean(all_vals) if all_vals else 50.0
        else:
            score = statistics.mean(sub_scores)

        return DimensionScore(
            dimension=Dimension.COMMUNICATION,
            score=round(max(0.0, min(100.0, score)), 1),
            metrics=metrics,
            data_point_count=len(records),
        )

    def _score_reliability(
        self, records: list[TransactionRecord], config: ScoringConfig
    ) -> DimensionScore:
        """
        Reliability score based on fulfillment rate and consistency.

        Higher fulfillment + lower variance = higher score.
        """
        fulfillment_values = [
            r.metric_value for r in records
            if "fulfillment" in r.metric_name or "fill" in r.metric_name
        ]

        if not fulfillment_values:
            fulfillment_values = [r.metric_value for r in records]

        avg_fulfillment = statistics.mean(fulfillment_values) if fulfillment_values else 0.0
        fulfillment_score = avg_fulfillment * 100  # Assuming rate is 0.0–1.0

        metrics = [
            MetricDetail(
                metric_name="fulfillment_rate",
                value=round(avg_fulfillment * 100, 1),
                unit="%",
                sample_size=len(fulfillment_values),
                description=f"Order fulfillment rate: {avg_fulfillment*100:.1f}%",
            ),
        ]

        # Consistency bonus/penalty
        if len(fulfillment_values) > 1:
            consistency = statistics.stdev(fulfillment_values)
            # Lower variance = bonus (up to +10), higher = penalty
            consistency_modifier = max(-10.0, 10.0 - consistency * 100)
            fulfillment_score += consistency_modifier
            metrics.append(MetricDetail(
                metric_name="consistency",
                value=round(consistency, 3),
                unit="σ",
                sample_size=len(fulfillment_values),
                description=f"Fulfillment consistency (std dev): {consistency:.3f}",
            ))

        return DimensionScore(
            dimension=Dimension.RELIABILITY,
            score=round(max(0.0, min(100.0, fulfillment_score)), 1),
            metrics=metrics,
            data_point_count=len(records),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_weight(dimension: Dimension, config: ScoringConfig) -> float:
        """Get the user-configured weight for a dimension."""
        weight_map = {
            Dimension.QUALITY: config.weights.quality,
            Dimension.PRICING: config.weights.pricing,
            Dimension.DELIVERY: config.weights.delivery,
            Dimension.COMMUNICATION: config.weights.communication,
            Dimension.RELIABILITY: config.weights.reliability,
        }
        return weight_map[dimension]

    @staticmethod
    def _assign_tier(score: float, config: ScoringConfig) -> str:
        """Map a composite score to a tier label using user-defined boundaries."""
        for tier in config.tiers:
            if score >= tier.min_score:
                return tier.name
        return config.tiers[-1].name if config.tiers else "Unclassified"

    async def _get_records(
        self,
        supplier_id: str,
        dimension: Dimension,
        start: datetime,
        end: datetime,
    ) -> list[TransactionRecord]:
        """Fetch TransactionRecords for a supplier/dimension/window."""
        stmt = (
            select(TransactionRecord)
            .where(
                and_(
                    TransactionRecord.supplier_id == supplier_id,
                    TransactionRecord.dimension == dimension,
                    TransactionRecord.record_date >= start,
                    TransactionRecord.record_date <= end,
                )
            )
            .order_by(TransactionRecord.record_date)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _has_records_in_window(
        self, supplier_id: str, start: datetime, end: datetime
    ) -> bool:
        """Check if any records exist in a time window."""
        stmt = (
            select(TransactionRecord.id)
            .where(
                and_(
                    TransactionRecord.supplier_id == supplier_id,
                    TransactionRecord.record_date >= start,
                    TransactionRecord.record_date <= end,
                )
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _compute_prior_composite_from_partitioned(
        self,
        prior_records: dict[Dimension, list[TransactionRecord]],
        config: ScoringConfig,
    ) -> float | None:
        """Compute composite score from in-memory partitioned records (zero DB queries)."""
        dim_scores: dict[str, float] = {}
        available_weight = 0.0

        for dimension in Dimension:
            records = prior_records.get(dimension, [])
            if not records:
                continue

            ds = self._compute_dimension_score(dimension, records, config)
            dim_scores[dimension.value] = ds.score
            available_weight += self._get_weight(dimension, config)

        if available_weight == 0:
            return None

        composite = 0.0
        for dim_name, score in dim_scores.items():
            dimension = Dimension(dim_name)
            weight = self._get_weight(dimension, config)
            composite += score * (weight / available_weight)

        return round(composite, 1)

    async def _compute_prior_composite(
        self,
        supplier_id: str,
        config: ScoringConfig,
        start: datetime,
        end: datetime,
    ) -> float | None:
        """Compute composite score for a prior period (for trend calculation)."""
        dim_scores: dict[str, float] = {}
        available_weight = 0.0

        for dimension in Dimension:
            records = await self._get_records(supplier_id, dimension, start, end)
            if not records:
                continue

            ds = self._compute_dimension_score(dimension, records, config)
            dim_scores[dimension.value] = ds.score
            available_weight += self._get_weight(dimension, config)

        if available_weight == 0:
            return None

        composite = 0.0
        for dim_name, score in dim_scores.items():
            dimension = Dimension(dim_name)
            weight = self._get_weight(dimension, config)
            composite += score * (weight / available_weight)

        return round(composite, 1)

    async def save_snapshot(
        self,
        supplier_id: str,
        composite: CompositeScore,
    ) -> list[ScoreSnapshot]:
        """Persist score snapshots to the database."""
        snapshots: list[ScoreSnapshot] = []

        # Save per-dimension scores
        for dim_name, dim_score in composite.dimension_scores.items():
            snapshot = ScoreSnapshot(
                supplier_id=supplier_id,
                dimension=Dimension(dim_name),
                score=dim_score.score,
                metric_details={
                    m.metric_name: {
                        "value": m.value,
                        "unit": m.unit,
                        "sample_size": m.sample_size,
                        "description": m.description,
                    }
                    for m in dim_score.metrics
                },
                window_start=dim_score.window_start or datetime.now(timezone.utc),
                window_end=dim_score.window_end or datetime.now(timezone.utc),
                config_version=composite.config_version,
            )
            self.session.add(snapshot)
            snapshots.append(snapshot)

        # Save composite
        now = datetime.now(timezone.utc)
        composite_snapshot = ScoreSnapshot(
            supplier_id=supplier_id,
            dimension=None,
            score=composite.score,
            metric_details={
                "dimension_scores": {
                    k: v.score for k, v in composite.dimension_scores.items()
                },
                "prior_score": composite.prior_score,
            },
            window_start=now - timedelta(days=90),
            window_end=now,
            tier=composite.tier,
            trend=composite.trend,
            config_version=composite.config_version,
        )
        self.session.add(composite_snapshot)
        snapshots.append(composite_snapshot)

        await self.session.flush()
        return snapshots
