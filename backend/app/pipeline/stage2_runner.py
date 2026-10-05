"""
Stage 2 Batch Scoring Runner

Picks up all Stage-1-flagged reports that haven't been scored by Stage 2 yet,
runs them through the Stage 2 classifier, and persists the results.

Can be called:
  - via POST /api/v1/score/run (API trigger)
  - directly: backend\\venv\\Scripts\\python backend\\app\\pipeline\\stage2_runner.py
"""
import asyncio
import logging
import sys
from pathlib import Path

log = logging.getLogger("SIH165.stage2_runner")
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")

# Allow running directly from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def run_stage2_batch(db=None, limit: int = 500):
    """
    Score all Stage-1-flagged, Stage-2-unscored reports.
    If db is None, opens its own session (standalone mode).
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    from app.db.models import Report, FeatureVector, Prediction, AuditLog
    from app.pipeline.stage2_classifier import stage2_classifier
    from app.core.config import settings

    # Use the same configured database as the API server. The former
    # launch-directory-relative path could create a second, empty database.
    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    own_session = db is None

    if own_session:
        db = Session()

    try:
        # Fetch reports: Stage 1 flagged but Stage 2 not yet run (sif_flag is NULL)
        stmt = (
            select(Report, FeatureVector, Prediction)
            .join(FeatureVector, FeatureVector.report_id == Report.id)
            .join(Prediction, Prediction.report_id == Report.id)
            .where(
                Prediction.stage1_flagged == True,
                Prediction.sif_flag == None,
            )
            .limit(limit)
        )
        rows = (await db.execute(stmt)).all()

        log.info(f"Stage 2 batch: {len(rows)} reports to score.")

        scored = 0
        for row in rows:
            report  = row.Report
            fv      = row.FeatureVector
            pred    = row.Prediction

            try:
                result = stage2_classifier.predict(
                    report_text       = report.report_text,
                    critical_risk     = report.critical_risk,
                    has_site_metadata = report.has_site_metadata,
                    has_shift_metadata= report.has_shift_metadata,
                    hi_po             = fv.hi_po or False,
                    stage1_score      = pred.stage1_score or 0.0,
                )

                # Update prediction row
                pred.sif_flag          = result.sif_flag
                pred.calibrated_prob   = result.calibrated_prob
                pred.confidence_band   = result.confidence_band
                pred.operational_state = result.operational_state
                pred.iogp_rules        = result.iogp_rules
                pred.cause_categories  = result.cause_categories
                pred.ood_score         = result.ood_score
                pred.routing_reason    = result.routing_reason
                pred.shap_values       = result.shap_values
                pred.ig_spans          = result.ig_spans

                # Update feature vector barrier status
                fv.barrier_status      = fv.barrier_status  # already set at ingestion

                # Audit
                db.add(AuditLog(
                    report_id    = report.id,
                    event_type   = "PREDICTED",
                    model_score  = result.calibrated_prob,
                    metadata_json= {
                        "confidence_band":   result.confidence_band,
                        "operational_state": result.operational_state,
                        "iogp_rules":        result.iogp_rules,
                        "ood_score":         result.ood_score,
                        "mode":              "trained" if stage2_classifier._loaded else "heuristic",
                    }
                ))
                scored += 1

            except Exception as e:
                log.error(f"Stage 2 failed for report {report.id[:8]}: {e}")

        await db.commit()
        log.info(f"Stage 2 batch complete: {scored}/{len(rows)} reports scored.")
        return {"scored": scored, "total": len(rows)}

    finally:
        if own_session:
            await db.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_stage2_batch())
