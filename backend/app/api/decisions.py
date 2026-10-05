"""Officer Decisions router — POST /api/v1/reports/{id}/decision"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import OfficerDecision, AuditLog, ActiveLearningQueue, Prediction, DecisionType

router = APIRouter()


class DecisionRequest(BaseModel):
    officer_id: str = Field(..., description="Anonymized officer identifier")
    officer_role: str = Field(default="safety_officer")
    decision: str = Field(..., description="AGREE or DISAGREE")
    notes: str = Field(default="")


@router.post(
    "/reports/{report_id}/decision",
    summary="Submit officer agree/disagree decision on a report",
)
async def submit_decision(
    report_id: str,
    body: DecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Human-in-the-loop validation endpoint.

    - Stores the officer decision
    - Writes to the immutable audit log
    - If DISAGREE: adds to active learning queue for future retraining
    """
    if body.decision not in (DecisionType.AGREE, DecisionType.DISAGREE):
        raise HTTPException(status_code=400, detail="decision must be AGREE or DISAGREE")

    # Check if decision already exists
    existing = await db.execute(
        select(OfficerDecision).where(OfficerDecision.report_id == report_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Decision already recorded for this report")

    # Fetch current model score for audit
    pred_row = await db.execute(
        select(Prediction).where(Prediction.report_id == report_id)
    )
    pred = pred_row.scalar_one_or_none()
    model_score = pred.calibrated_prob if pred else None

    # Persist decision
    decision = OfficerDecision(
        report_id=report_id,
        officer_id=body.officer_id,
        officer_role=body.officer_role,
        decision=body.decision,
        notes=body.notes,
    )
    db.add(decision)

    # Audit log entry (immutable)
    audit = AuditLog(
        report_id=report_id,
        event_type="DECIDED",
        model_score=model_score,
        officer_action=body.decision,
        officer_role=body.officer_role,
        metadata_json={"notes": body.notes},
    )
    db.add(audit)

    # If officer disagrees → seed active learning queue
    if body.decision == DecisionType.DISAGREE:
        al = ActiveLearningQueue(
            report_id=report_id,
            model_prob=model_score,
            queue_reason="OFFICER_DISAGREE",
            status="PENDING",
        )
        db.add(al)

    await db.commit()
    return {"status": "recorded", "report_id": report_id, "decision": body.decision}
