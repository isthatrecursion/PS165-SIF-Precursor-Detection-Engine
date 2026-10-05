"""Reports API router — GET /api/v1/reports, GET /api/v1/reports/{id}"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import Report, Prediction, FeatureVector, OfficerDecision

router = APIRouter()


@router.get("/reports", summary="Paginated report queue with filters")
async def list_reports(
    site: Optional[str] = Query(None),
    confidence_band: Optional[str] = Query(None, description="HIGH / LOW / AMBIGUOUS / OOD"),
    iogp_rule: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="UNREVIEWED / REVIEWED"),
    stage1_flagged: Optional[bool] = Query(None),
    sif_flag: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Paginated, filtered report queue.
    Sorted by calibrated_prob descending (highest risk first).
    Returns total_count (all matching rows), sif_flagged_count, and needs_review_count
    for accurate stat cards independent of pagination.
    """
    from sqlalchemy import nulls_last, desc

    def _build_filters():
        f = []
        if site:
            f.append(Report.site == site)
        if confidence_band:
            f.append(Prediction.confidence_band == confidence_band)
        if stage1_flagged is not None:
            f.append(Prediction.stage1_flagged == stage1_flagged)
        if sif_flag is not None:
            f.append(Prediction.sif_flag == sif_flag)
        if status == "UNREVIEWED":
            f.append(OfficerDecision.id == None)   # noqa: E711
        elif status == "REVIEWED":
            f.append(OfficerDecision.id != None)   # noqa: E711
        return f

    filter_clauses = _build_filters()

    def _base():
        q = (
            select(Report, Prediction, OfficerDecision)
            .outerjoin(Prediction, Prediction.report_id == Report.id)
            .outerjoin(OfficerDecision, OfficerDecision.report_id == Report.id)
        )
        if filter_clauses:
            q = q.where(and_(*filter_clauses))
        return q

    # ── Total count (for pagination and stat card) ────────────────────────────
    count_q = (
        select(func.count(Report.id))
        .outerjoin(Prediction, Prediction.report_id == Report.id)
        .outerjoin(OfficerDecision, OfficerDecision.report_id == Report.id)
    )
    if filter_clauses:
        count_q = count_q.where(and_(*filter_clauses))
    total_count = (await db.execute(count_q)).scalar() or 0

    # ── SIF-flagged count within current filter ───────────────────────────────
    sif_q = (
        select(func.count(Report.id))
        .outerjoin(Prediction, Prediction.report_id == Report.id)
        .outerjoin(OfficerDecision, OfficerDecision.report_id == Report.id)
        .where(Prediction.sif_flag == True)   # noqa: E712
    )
    if filter_clauses:
        sif_q = sif_q.where(and_(*filter_clauses))
    sif_total = (await db.execute(sif_q)).scalar() or 0

    # ── NEEDS_REVIEW count within current filter ──────────────────────────────
    nr_q = (
        select(func.count(Report.id))
        .outerjoin(Prediction, Prediction.report_id == Report.id)
        .outerjoin(OfficerDecision, OfficerDecision.report_id == Report.id)
        .where(Prediction.operational_state == "NEEDS_REVIEW")
    )
    if filter_clauses:
        nr_q = nr_q.where(and_(*filter_clauses))
    nr_total = (await db.execute(nr_q)).scalar() or 0

    # ── Paginated rows ────────────────────────────────────────────────────────
    stmt = _base().order_by(nulls_last(desc(Prediction.calibrated_prob)))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).all()

    # iogp_rule: JSON array in SQLite — post-filter in Python
    if iogp_rule:
        rows = [r for r in rows if r.Prediction and iogp_rule in (r.Prediction.iogp_rules or [])]

    return {
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "sif_flagged_count": sif_total,
        "needs_review_count": nr_total,
        "count": len(rows),
        "reports": [
            {
                "id": r.Report.id,
                "site": r.Report.site,
                "shift_date": r.Report.shift_date,
                "reporter_role": r.Report.reporter_role,
                "ingest_status": r.Report.ingest_status,
                "text_only_mode": r.Report.text_only_mode,
                "stage1_flagged": r.Prediction.stage1_flagged if r.Prediction else None,
                "sif_flag": r.Prediction.sif_flag if r.Prediction else None,
                "calibrated_prob": r.Prediction.calibrated_prob if r.Prediction else None,
                "confidence_band": r.Prediction.confidence_band if r.Prediction else None,
                "iogp_rules": r.Prediction.iogp_rules if r.Prediction else [],
                "operational_state": r.Prediction.operational_state if r.Prediction else None,
                "routing_reason": r.Prediction.routing_reason if r.Prediction else None,
                "decision": r.OfficerDecision.decision if r.OfficerDecision else None,
            }
            for r in rows
        ],
    }



@router.get("/reports/{report_id}", summary="Full report detail with predictions and XAI")
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the complete report including:
      - Full narrative text
      - Feature extraction results (energy types, barrier status, etc.)
      - Stage 2 prediction (calibrated prob, IOGP rules, cause categories)
      - Explainability: SHAP values + IG text spans
      - Officer decision if one exists
    Used by the Officer Card / Report Detail view.
    """
    stmt = (
        select(Report)
        .where(Report.id == report_id)
        .options(
            selectinload(Report.features),
            selectinload(Report.prediction),
            selectinload(Report.decision),
        )
    )
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    pred = report.prediction
    feat = report.features
    dec  = report.decision

    return {
        "id": report.id,
        "site": report.site,
        "country": report.country,
        "industry_sector": report.industry_sector,
        "shift_date": report.shift_date,
        # IMPORTANT: reporter_role only — NO reporter identity (Section 18)
        "reporter_role": report.reporter_role,
        "report_text": report.report_text,
        "report_type": report.report_type,
        "critical_risk": report.critical_risk,
        "ingest_status": report.ingest_status,
        "text_only_mode": report.text_only_mode,
        "lower_confidence_flag": report.lower_confidence_flag,
        # Domain features
        "features": {
            "energy_types": feat.energy_types if feat else [],
            "barrier_phrases": feat.barrier_phrases if feat else [],
            "barrier_status": feat.barrier_status if feat else "UNKNOWN",
            "has_energy_signal": feat.has_energy_signal if feat else False,
            "has_barrier_failure": feat.has_barrier_failure if feat else False,
            "hazard_categories": feat.hazard_categories if feat else [],
            "safety_mgmt_terms": feat.safety_mgmt_terms if feat else [],
            "equipment_terms": feat.equipment_terms if feat else [],
            "interlock_bypass_detected": feat.interlock_bypass_detected if feat else False,
            "hi_po": feat.hi_po if feat else None,
            "accident_level": feat.accident_level if feat else None,
            "potential_accident_level": feat.potential_accident_level if feat else None,
        } if feat else None,
        # Predictions
        "prediction": {
            "stage1_flagged": pred.stage1_flagged,
            "sif_flag": pred.sif_flag,
            "calibrated_prob": pred.calibrated_prob,
            "confidence_band": pred.confidence_band,
            "operational_state": pred.operational_state,
            "iogp_rules": pred.iogp_rules or [],
            "cause_categories": pred.cause_categories or [],
            "ood_score": pred.ood_score,
            "routing_reason": pred.routing_reason,
            # XAI
            "shap_values": pred.shap_values or {},
            "ig_spans": pred.ig_spans or [],
        } if pred else None,
        # Officer decision
        "decision": {
            "decision": dec.decision,
            "officer_role": dec.officer_role,
            "notes": dec.notes,
            "created_at": dec.created_at,
        } if dec else None,
    }


@router.get("/queue/manual-review", summary="Manual review queue")
async def manual_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Reports routed away from automated scoring.
    Reasons: OCR_FAILED, LOW_CONFIDENCE, AMBIGUOUS_OOD, MISSING_METADATA.
    Used by the Manual Review Queue view.
    """
    from app.db.models import IngestStatus
    stmt = (
        select(Report, Prediction)
        .outerjoin(Prediction, Prediction.report_id == Report.id)
        .where(
            (Report.ingest_status == IngestStatus.MANUAL_REVIEW) |
            (Prediction.confidence_band.in_(["LOW", "AMBIGUOUS", "OOD"])) |
            (Report.lower_confidence_flag == True)   # noqa: E712
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return {
        "page": page,
        "page_size": page_size,
        "count": len(rows),
        "reports": [
            {
                "id": r.Report.id,
                "site": r.Report.site,
                "shift_date": r.Report.shift_date,
                "ingest_status": r.Report.ingest_status,
                "routing_reason": r.Prediction.routing_reason if r.Prediction else "UNKNOWN",
                "confidence_band": r.Prediction.confidence_band if r.Prediction else None,
            }
            for r in rows
        ],
    }
