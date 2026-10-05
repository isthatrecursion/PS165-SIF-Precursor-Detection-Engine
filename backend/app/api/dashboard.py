"""Leadership Dashboard router — GET /api/v1/dashboard/"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Report, Prediction, FeatureVector

router = APIRouter()


@router.get("/dashboard/leadership", summary="Aggregated leadership analytics (no individual reports)")
async def leadership_dashboard(
    site: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregation-only view for Site/Regional HSE Leadership.

    IMPORTANT: This endpoint intentionally returns NO individual report data.
    It aggregates across reports to show trends, cluster density,
    and per-site pattern information only.
    """
    # Panel 1: SIF counts by site
    stmt = (
        select(
            Report.site,
            func.count(Prediction.id).label("total"),
            func.sum(case((Prediction.sif_flag == True, 1), else_=0)).label("sif_count"),   # noqa: E712
            func.sum(case((Prediction.stage1_flagged == True, 1), else_=0)).label("flagged_count"),
        )
        .outerjoin(Prediction, Prediction.report_id == Report.id)
        .group_by(Report.site)
    )
    if site:
        stmt = stmt.where(Report.site == site)

    result = await db.execute(stmt)
    site_rows = result.all()

    # Panel 2: IOGP rule frequency — expand JSON array
    # Simplified: count predictions that have each rule listed
    pred_stmt = select(Prediction.iogp_rules, Prediction.cause_categories).where(
        Prediction.sif_flag == True  # noqa: E712
    )
    pred_result = await db.execute(pred_stmt)
    pred_rows = pred_result.all()

    rule_counts: dict = {}
    cause_counts: dict = {}
    for row in pred_rows:
        for rule in (row.iogp_rules or []):
            rule_counts[rule] = rule_counts.get(rule, 0) + 1
        for cause in (row.cause_categories or []):
            cause_counts[cause] = cause_counts.get(cause, 0) + 1

    # Panel 3: Barrier failure trends by site
    barrier_stmt = (
        select(Report.site, FeatureVector.barrier_status, func.count().label("count"))
        .join(FeatureVector, FeatureVector.report_id == Report.id)
        .where(FeatureVector.has_barrier_failure == True)   # noqa: E712
        .group_by(Report.site, FeatureVector.barrier_status)
    )
    barrier_result = await db.execute(barrier_stmt)
    barrier_rows = barrier_result.all()

    return {
        # NOTE: no individual report identifiers, text, or reporter info returned
        "site_summary": [
            {
                "site": r.site,
                "industry_sector": "",
                "total_reports": r.total,
                "sif_precursor_count": int(r.sif_count or 0),
                "stage1_flagged_count": int(r.flagged_count or 0),
                "sif_rate_pct": round(
                    ((r.sif_count or 0) / r.total * 100) if r.total else 0, 1
                ),
            }
            for r in site_rows
        ],
        "iogp_rule_frequency": [
            {"rule": rule, "count": count}
            for rule, count in sorted(rule_counts.items(), key=lambda x: -x[1])
        ],
        "cause_category_frequency": [
            {"cause": cause, "count": count}
            for cause, count in sorted(cause_counts.items(), key=lambda x: -x[1])
        ],
        "barrier_failure_by_site": [
            {"site": r.site, "barrier_status": r.barrier_status, "count": r.count}
            for r in barrier_rows
        ],
    }


@router.get("/dashboard/site-recall", summary="Per-site model recall audit (data equity check)")
async def site_recall_audit(db: AsyncSession = Depends(get_db)):
    """
    Site-level recall audit panel.
    Compares SIF detection rate across sites to surface where the model
    may be underperforming relative to the overall average.
    (Section 8.3 — Per-Site Recall Audit)
    """
    stmt = (
        select(
            Report.site,
            func.count(Report.id).label("total"),
            func.sum(
                case((FeatureVector.hi_po == True, 1), else_=0)  # noqa: E712
            ).label("actual_hipo"),
            func.sum(
                case((Prediction.sif_flag == True, 1), else_=0)  # noqa: E712
            ).label("predicted_sif"),
        )
        .outerjoin(FeatureVector, FeatureVector.report_id == Report.id)
        .outerjoin(Prediction, Prediction.report_id == Report.id)
        .group_by(Report.site)
    )
    result = await db.execute(stmt)
    rows = result.all()

    site_data = []
    for r in rows:
        actual  = int(r.actual_hipo or 0)
        pred    = int(r.predicted_sif or 0)
        recall  = round(pred / actual, 3) if actual > 0 else None
        site_data.append({
            "site": r.site,
            "total_reports": r.total,
            "hi_po_count": actual,
            "sif_predicted": pred,
            "proxy_recall": recall,
        })

    # Flag sites below average recall
    recalls = [s["proxy_recall"] for s in site_data if s["proxy_recall"] is not None]
    avg_recall = round(sum(recalls) / len(recalls), 3) if recalls else None

    for s in site_data:
        s["below_average"] = (
            s["proxy_recall"] is not None and avg_recall is not None
            and s["proxy_recall"] < avg_recall
        )

    return {
        "average_proxy_recall": avg_recall,
        "sites": site_data,
    }


@router.get("/dashboard/activity-breakdown", summary="SIF density by activity type (IOGP-rule-derived)")
async def activity_breakdown(db: AsyncSession = Depends(get_db)):
    """
    Surfaces recurring precursor patterns by ACTIVITY TYPE.

    Activity type is derived from IOGP Life-Saving Rule tags — each rule
    corresponds to a distinct hazardous activity (Hot Work, Energy Isolation,
    Confined Space Entry, Working at Height, Lifting, Driving, SIMOPS, etc.).

    Returns:
      activity_density  — SIF count + total + SIF rate per activity type,
                          sorted by SIF rate descending (highest risk activity first)
      site_activity     — site × activity cross-tab (count of SIF reports per cell)
    """
    # Pull all SIF-flagged predictions and their IOGP rules
    all_stmt = select(
        Prediction.iogp_rules,
        Prediction.sif_flag,
        Report.site,
    ).join(Report, Report.id == Prediction.report_id)

    result = await db.execute(all_stmt)
    rows = result.all()

    # Activity density: count total reports + SIF reports per IOGP rule
    activity_total: dict = {}
    activity_sif:   dict = {}
    # Site × activity matrix: {site: {activity: sif_count}}
    site_activity:  dict = {}

    for row in rows:
        rules = row.iogp_rules or []
        is_sif = bool(row.sif_flag)
        site = row.site or "Unknown"

        for rule in rules:
            activity_total[rule] = activity_total.get(rule, 0) + 1
            if is_sif:
                activity_sif[rule] = activity_sif.get(rule, 0) + 1
                # Site × activity
                if site not in site_activity:
                    site_activity[site] = {}
                site_activity[site][rule] = site_activity[site].get(rule, 0) + 1

    # Build density list
    all_activities = set(list(activity_total.keys()) + list(activity_sif.keys()))
    density = []
    for act in all_activities:
        total = activity_total.get(act, 0)
        sif   = activity_sif.get(act, 0)
        density.append({
            "activity": act,
            "total_reports": total,
            "sif_count": sif,
            "sif_rate_pct": round(sif / total * 100, 1) if total > 0 else 0.0,
        })
    density.sort(key=lambda x: -x["sif_rate_pct"])

    # Flatten site × activity for frontend
    site_activity_flat = [
        {"site": site, "activity": act, "sif_count": count}
        for site, acts in site_activity.items()
        for act, count in acts.items()
    ]
    # Sort by SIF count desc
    site_activity_flat.sort(key=lambda x: -x["sif_count"])

    return {
        "activity_density": density,
        "site_activity_matrix": site_activity_flat,
    }


@router.get("/dashboard/trend", summary="Monthly SIF precursor trend (time-series)")
async def sif_trend(
    site: Optional[str] = Query(None, description="Filter by site name"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns monthly SIF precursor counts and rates over time.
    Used by the leadership trend chart to show if a site (or all sites)
    is trending riskier.

    Groups by year-month of shift_date. Reports with no date are excluded.
    """
    from sqlalchemy import extract

    stmt = select(
        Report.shift_date,
        Report.site,
        Prediction.sif_flag,
    ).join(
        Prediction, Prediction.report_id == Report.id
    ).where(
        Report.shift_date.isnot(None)
    )

    if site:
        stmt = stmt.where(Report.site == site)

    result = await db.execute(stmt)
    rows = result.all()

    # Group by year-month
    monthly: dict = {}   # "YYYY-MM" → {"total": int, "sif": int}
    for row in rows:
        ym = row.shift_date.strftime("%Y-%m")
        if ym not in monthly:
            monthly[ym] = {"total": 0, "sif": 0}
        monthly[ym]["total"] += 1
        if row.sif_flag:
            monthly[ym]["sif"] += 1

    trend = [
        {
            "month": ym,
            "total_reports": v["total"],
            "sif_count": v["sif"],
            "sif_rate_pct": round(v["sif"] / v["total"] * 100, 1) if v["total"] > 0 else 0.0,
        }
        for ym, v in sorted(monthly.items())
    ]

    return {
        "site_filter": site or "All Sites",
        "trend": trend,
    }
