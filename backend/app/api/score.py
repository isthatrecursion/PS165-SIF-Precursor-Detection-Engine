"""Score trigger router — POST /api/v1/score/run"""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db

router = APIRouter()


@router.post("/score/run", summary="Trigger Stage 2 batch scoring on all pending Stage-1-flagged reports")
async def trigger_stage2(
    background_tasks: BackgroundTasks,
    limit: int = 500,
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers Stage 2 classifier over all Stage-1-flagged reports
    that haven't been Stage-2 scored yet.

    Runs in background — returns immediately with job info.
    Poll GET /api/v1/score/status for completion.
    """
    from app.pipeline.stage2_runner import run_stage2_batch
    background_tasks.add_task(run_stage2_batch, limit=limit)
    return {"status": "started", "message": f"Stage 2 scoring queued for up to {limit} reports."}


@router.get("/score/status", summary="Stage 2 scoring status summary")
async def score_status(db: AsyncSession = Depends(get_db)):
    """Returns count of reports at each scoring state."""
    from sqlalchemy import select, func, case
    from app.db.models import Prediction

    result = await db.execute(
        select(
            func.count(Prediction.id).label("total"),
            func.sum(case((Prediction.sif_flag == None, 1), else_=0)).label("unscored"),
            func.sum(case((Prediction.sif_flag == True,  1), else_=0)).label("sif_flagged"),
            func.sum(case((Prediction.sif_flag == False, 1), else_=0)).label("non_sif"),
            func.sum(case((Prediction.operational_state == "NEEDS_REVIEW", 1), else_=0)).label("needs_review"),
        )
    )
    row = result.one()
    return {
        "total_predictions": row.total,
        "stage2_unscored":   row.unscored,
        "sif_flagged":       row.sif_flagged,
        "non_sif":           row.non_sif,
        "needs_review":      row.needs_review,
    }
