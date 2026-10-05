"""Audit Log router"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import AuditLog

router = APIRouter()

@router.get("/audit-log", summary="Filterable audit log of all officer decisions")
async def get_audit_log(
    report_id: str = Query(None),
    event_type: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if report_id:
        stmt = stmt.where(AuditLog.report_id == report_id)
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {
        "count": len(rows),
        "entries": [
            {
                "id": r.id,
                "report_id": r.report_id,
                "event_type": r.event_type,
                "model_score": r.model_score,
                "officer_action": r.officer_action,
                "officer_role": r.officer_role,
                "timestamp": r.timestamp,
            }
            for r in rows
        ],
    }
