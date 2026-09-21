"""
Scorecards route — supplier scorecard retrieval.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_user_id
from src.data.models import Supplier, ScoreSnapshot

router = APIRouter()


class ScorecardResponse(BaseModel):
    """Supplier scorecard data."""
    supplier_id: str
    supplier_name: str
    composite_score: float | None = None
    tier: str | None = None
    trend: str | None = None
    dimensions: dict | None = None
    computed_at: str | None = None


@router.get("/scorecards", response_model=list[ScorecardResponse])
async def list_scorecards(
    supplier_ids: str | None = Query(default=None, description="Optional comma-separated list of supplier IDs"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Get latest scorecards for all suppliers (or filtered by IDs),
    scoped to the authenticated user.
    """
    stmt = select(Supplier).where(Supplier.user_id == user_id).order_by(Supplier.name)
    if supplier_ids:
        ids_list = [i.strip() for i in supplier_ids.split(",") if i.strip()]
        if ids_list:
            stmt = stmt.where(Supplier.id.in_(ids_list))
    result = await db.execute(stmt)
    suppliers = result.scalars().all()

    if not suppliers:
        return []

    sup_ids = [s.id for s in suppliers]

    # Optimization: Use SQL subquery to fetch ONLY the latest composite snapshot per supplier
    latest_subq = (
        select(
            ScoreSnapshot.supplier_id,
            func.max(ScoreSnapshot.computed_at).label("max_computed"),
        )
        .where(
            ScoreSnapshot.supplier_id.in_(sup_ids),
            ScoreSnapshot.dimension.is_(None),
        )
        .group_by(ScoreSnapshot.supplier_id)
        .subquery()
    )

    stmt_comp = (
        select(ScoreSnapshot)
        .join(
            latest_subq,
            and_(
                ScoreSnapshot.supplier_id == latest_subq.c.supplier_id,
                ScoreSnapshot.computed_at == latest_subq.c.max_computed,
                ScoreSnapshot.dimension.is_(None),
            ),
        )
    )
    res_comp = await db.execute(stmt_comp)
    latest_composites: dict[str, ScoreSnapshot] = {
        comp.supplier_id: comp for comp in res_comp.scalars().all()
    }

    # Fetch dimension snapshots only for those exact latest timestamps
    dim_map: dict[str, dict] = {}
    if latest_composites:
        stmt_dims = (
            select(ScoreSnapshot)
            .join(
                latest_subq,
                and_(
                    ScoreSnapshot.supplier_id == latest_subq.c.supplier_id,
                    ScoreSnapshot.computed_at == latest_subq.c.max_computed,
                    ScoreSnapshot.dimension.isnot(None),
                ),
            )
        )
        res_dims = await db.execute(stmt_dims)
        for d in res_dims.scalars().all():
            if d.supplier_id not in dim_map:
                dim_map[d.supplier_id] = {}
            dim_map[d.supplier_id][d.dimension.value] = {
                "score": d.score,
                "details": d.metric_details,
            }

    responses: list[ScorecardResponse] = []
    for sup in suppliers:
        comp = latest_composites.get(sup.id)
        if comp:
            dims = dim_map.get(sup.id, {})
            if not dims and comp.metric_details and isinstance(comp.metric_details, dict):
                raw_dims = comp.metric_details.get("dimension_scores", {})
                dims = {k: {"score": v} for k, v in raw_dims.items()}
            responses.append(
                ScorecardResponse(
                    supplier_id=sup.id,
                    supplier_name=sup.name,
                    composite_score=comp.score,
                    tier=comp.tier,
                    trend=comp.trend,
                    dimensions=dims,
                    computed_at=comp.computed_at.isoformat() if comp.computed_at else None,
                )
            )
        else:
            responses.append(
                ScorecardResponse(
                    supplier_id=sup.id,
                    supplier_name=sup.name,
                )
            )

    return responses


@router.get("/scorecards/{supplier_id}", response_model=ScorecardResponse)
async def get_scorecard(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Get the latest scorecard for a supplier, verifying ownership."""
    # Get supplier (scoped to user)
    stmt = select(Supplier).where(Supplier.id == supplier_id, Supplier.user_id == user_id)
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")

    # Get latest composite score snapshot
    stmt = (
        select(ScoreSnapshot)
        .where(
            ScoreSnapshot.supplier_id == supplier_id,
            ScoreSnapshot.dimension.is_(None),  # Composite scores have NULL dimension
        )
        .order_by(desc(ScoreSnapshot.computed_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    composite = result.scalar_one_or_none()

    if not composite:
        return ScorecardResponse(
            supplier_id=supplier.id,
            supplier_name=supplier.name,
        )

    # Get per-dimension scores
    stmt = (
        select(ScoreSnapshot)
        .where(
            ScoreSnapshot.supplier_id == supplier_id,
            ScoreSnapshot.dimension.isnot(None),
            ScoreSnapshot.computed_at == composite.computed_at,
        )
    )
    result = await db.execute(stmt)
    dim_snapshots = result.scalars().all()

    dimensions = {}
    for snap in dim_snapshots:
        dimensions[snap.dimension.value] = {
            "score": snap.score,
            "details": snap.metric_details,
        }

    if not dimensions and composite.metric_details and isinstance(composite.metric_details, dict):
        raw_dims = composite.metric_details.get("dimension_scores", {})
        dimensions = {k: {"score": v} for k, v in raw_dims.items()}

    return ScorecardResponse(
        supplier_id=supplier.id,
        supplier_name=supplier.name,
        composite_score=composite.score,
        tier=composite.tier,
        trend=composite.trend,
        dimensions=dimensions,
        computed_at=composite.computed_at.isoformat() if composite.computed_at else None,
    )

