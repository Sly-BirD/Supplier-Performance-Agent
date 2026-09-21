"""
Suppliers route — supplier listing and management.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_user_id
from src.data.models import Supplier

router = APIRouter()


class SupplierResponse(BaseModel):
    """Supplier data."""
    id: str
    name: str
    category: str | None = None
    region: str | None = None
    contact_email: str | None = None
    is_active: bool
    created_at: str


class SupplierCreate(BaseModel):
    """Create a new supplier."""
    name: str
    category: str | None = None
    region: str | None = None
    contact_email: str | None = None


@router.get("/suppliers", response_model=list[SupplierResponse])
async def list_suppliers(
    category: str | None = Query(default=None),
    region: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """List suppliers with optional filtering, scoped to the authenticated user."""
    stmt = select(Supplier).where(Supplier.user_id == user_id).order_by(Supplier.name)

    if category:
        stmt = stmt.where(Supplier.category == category)
    if region:
        stmt = stmt.where(Supplier.region == region)
    if is_active is not None:
        stmt = stmt.where(Supplier.is_active == is_active)

    result = await db.execute(stmt)
    suppliers = result.scalars().all()

    return [
        SupplierResponse(
            id=s.id,
            name=s.name,
            category=s.category,
            region=s.region,
            contact_email=s.contact_email,
            is_active=s.is_active,
            created_at=s.created_at.isoformat() if s.created_at else "",
        )
        for s in suppliers
    ]


@router.post("/suppliers", response_model=SupplierResponse, status_code=201)
async def create_supplier(
    data: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Create a new supplier owned by the authenticated user."""
    supplier = Supplier(
        user_id=user_id,
        name=data.name,
        category=data.category,
        region=data.region,
        contact_email=data.contact_email,
    )
    db.add(supplier)
    await db.flush()

    return SupplierResponse(
        id=supplier.id,
        name=supplier.name,
        category=supplier.category,
        region=supplier.region,
        contact_email=supplier.contact_email,
        is_active=supplier.is_active,
        created_at=supplier.created_at.isoformat() if supplier.created_at else "",
    )


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """Get a single supplier by ID, verifying ownership."""
    stmt = select(Supplier).where(Supplier.id == supplier_id, Supplier.user_id == user_id)
    result = await db.execute(stmt)
    supplier = result.scalar_one_or_none()

    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    return SupplierResponse(
        id=supplier.id,
        name=supplier.name,
        category=supplier.category,
        region=supplier.region,
        contact_email=supplier.contact_email,
        is_active=supplier.is_active,
        created_at=supplier.created_at.isoformat() if supplier.created_at else "",
    )

