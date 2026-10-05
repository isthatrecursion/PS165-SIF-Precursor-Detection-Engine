"""Ingest API router — POST /api/v1/ingest"""
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.pipeline.ingestion_service import ingestion_service

router = APIRouter()


@router.post("/ingest", summary="Ingest a CSV or Excel file of safety reports")
async def ingest_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CSV or Excel file containing safety reports.
    Each row is processed through the OCR gate, feature extractor,
    and Stage 1 high-recall filter. Returns summary counts and report IDs.
    """
    allowed = {".csv", ".xlsx", ".xls"}
    suffix = "." + file.filename.split(".")[-1].lower()
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Accepted: {allowed}"
        )

    content = await file.read()
    try:
        result = await ingestion_service.ingest_file(
            file_content=content,
            filename=file.filename,
            db=db,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result
