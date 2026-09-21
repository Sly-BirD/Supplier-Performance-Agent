"""
Upload route — file ingestion and sample data seeding endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_user_id
from src.data.adapters.csv_adapter import CSVExcelAdapter
from src.data.importer import ingest_dataframe, seed_sample_datasets

router = APIRouter()


class UploadResponse(BaseModel):
    """Response after processing a file upload."""
    message: str
    source_id: str | None = None
    pending_approval: dict | None = None
    row_count: int | None = None
    column_count: int | None = None


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Upload a CSV or Excel file for ingestion and automatic scorecard computation.
    Data is scoped to the authenticated user.
    Supported formats: .csv, .tsv, .xlsx, .xls
    """
    allowed_extensions = {".csv", ".tsv", ".xlsx", ".xls", ".xlsm", ".txt"}
    filename = file.filename or "upload"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed_extensions)}",
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    try:
        # Extract raw DataFrame
        adapter = CSVExcelAdapter()
        df = adapter.extract_raw(content)

        # Ingest, score, and evaluate alerts (scoped to user)
        ingest_res = await ingest_dataframe(df, db, source_name=filename, user_id=user_id)

        return UploadResponse(
            message=f"✓ Successfully ingested {ingest_res['row_count']} rows across {ingest_res['suppliers_count']} suppliers. Computed scorecards and triggered {ingest_res['alerts_fired']} alerts.",
            row_count=ingest_res["row_count"],
            column_count=len(df.columns),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error ingesting file: {str(e)}",
        )


@router.post("/seed", response_model=UploadResponse)
async def seed_data(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Seed realistic multi-dimensional sample supplier data covering Quality,
    Delivery, Pricing, and Communication across 5 diverse suppliers.
    Data is scoped to the authenticated user.
    """
    try:
        res = await seed_sample_datasets(db, user_id=user_id)
        return UploadResponse(
            message=f"✓ Seeded sample dataset: {res['row_count']} records across {res['suppliers_count']} suppliers. {res['alerts_fired']} active alerts triggered.",
            row_count=res["row_count"],
            column_count=11,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error seeding sample data: {str(e)}",
        )

