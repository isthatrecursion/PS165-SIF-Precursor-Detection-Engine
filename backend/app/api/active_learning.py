"""Active Learning Queue router"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.db.database import get_db
from app.db.models import ActiveLearningQueue, Report

router = APIRouter()


class LabelRequest(BaseModel):
    corrected_sif: bool
    corrected_iogp: Optional[List[str]] = []
    corrected_cause: Optional[List[str]] = []
    labeled_by: str


@router.get("/active-learning/queue", summary="Active learning queue for relabeling")
async def get_al_queue(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ActiveLearningQueue, Report)
        .join(Report, Report.id == ActiveLearningQueue.report_id)
        .where(ActiveLearningQueue.status == "PENDING")
        .order_by(ActiveLearningQueue.model_prob)  # Lowest confidence first
    )
    result = await db.execute(stmt)
    rows = result.all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": r.ActiveLearningQueue.id,
                "report_id": r.ActiveLearningQueue.report_id,
                "model_prob": r.ActiveLearningQueue.model_prob,
                "queue_reason": r.ActiveLearningQueue.queue_reason,
                "report_text": r.Report.report_text,
                "reporter_role": r.Report.reporter_role,
                "site": r.Report.site,
            }
            for r in rows
        ],
    }


@router.post("/active-learning/{item_id}/label", summary="Submit corrected label")
async def submit_label(
    item_id: str,
    body: LabelRequest,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ActiveLearningQueue).where(ActiveLearningQueue.id == item_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    item.corrected_sif   = body.corrected_sif
    item.corrected_iogp  = body.corrected_iogp
    item.corrected_cause = body.corrected_cause
    item.labeled_by      = body.labeled_by
    item.labeled_at      = datetime.utcnow()
    item.status          = "LABELED"

    await db.commit()
    return {"status": "labeled", "item_id": item_id}
