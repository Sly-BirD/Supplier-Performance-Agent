"""
Comparison & Ranking Engine — Phase 4 stub.

Will support:
- Ranking suppliers within a category/region
- Normalizing scores for cross-category comparison
- Benchmark visualizations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class SupplierRanking:
    """A supplier's position in a comparative ranking."""

    supplier_id: str
    supplier_name: str
    composite_score: float
    rank: int
    category: str | None = None
    region: str | None = None
    dimension_scores: dict[str, float] = field(default_factory=dict)


class ComparisonEngine:
    """
    Stub: Comparison and ranking engine — planned for Phase 4.

    Will normalize and benchmark suppliers within the same
    category/region and produce ranked lists.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def rank_suppliers(
        self,
        supplier_ids: list[str],
        dimension: str | None = None,
    ) -> list[SupplierRanking]:
        """Rank suppliers by composite or dimension score."""
        raise NotImplementedError(
            "Comparison engine is planned for Phase 4. "
            "Use individual scorecards for now."
        )

    async def benchmark_category(
        self,
        category: str,
        region: str | None = None,
    ) -> list[SupplierRanking]:
        """Benchmark all suppliers within a category."""
        raise NotImplementedError(
            "Category benchmarking is planned for Phase 4."
        )
