"""
Ingestion Service — S2.2

Handles:
  1. Parsing CSV / Excel / JSON input
  2. OCR confidence gate (below threshold → MANUAL_REVIEW)
  3. Metadata completeness check → graceful degradation to text-only mode
  4. Domain feature extraction (Stage 2.3)
  5. Stage 1 filter (synchronous, inline)
  6. Persisting report + features + Stage 1 prediction to DB
  7. Routing decision: ROUTINE queue vs Stage 2 queue

Design principle (Section 29):
    Never fail silently into a falsely reassuring low-risk prediction.
    Insufficient info → MANUAL_REVIEW, not SIF=False.
"""
import io
import logging
import uuid
from datetime import datetime
from typing import List, Optional

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Report, FeatureVector, Prediction, AuditLog,
    IngestStatus, RoutingReason, ConfidenceBand
)
from app.pipeline.feature_extractor import extractor
from app.pipeline.stage1_filter import stage1_filter

logger = logging.getLogger(__name__)


# ── Column name mapping: IHMStefanini legacy CSV → internal schema ──────────
# Kept for backward-compatibility when users upload old CSV files.
# The new synthetic JSONL dataset already uses internal field names directly
# (report_text, site, date, shift, equipment_type, reporter_role, hi_po, etc.)

COLUMN_MAP = {
    "Data":                      "shift_date",
    "Countries":                 "country",
    "Local":                     "site",
    "Industry Sector":           "industry_sector",
    "Accident Level":            "accident_level",
    "Potential Accident Level":  "potential_accident_level",
    "Genre":                     "genre",
    "Employee or Third Party":   "reporter_role",
    "Employee ou Terceiro":      "reporter_role",   # Portuguese variant
    "Critical Risk":             "critical_risk",
    "Risco Critico":             "critical_risk",   # Portuguese variant
    "Description":               "report_text",
}

# Potential Accident Levels that qualify as Hi-Po (SIF candidate)
HIPO_LEVELS = {"IV", "V", "VI"}


class IngestionService:
    """
    Processes a file upload or a list of raw records into the pipeline.
    """

    async def ingest_file(
        self,
        file_content: bytes,
        filename: str,
        db: AsyncSession,
        ocr_confidence: float = 1.0,
    ) -> dict:
        """Parse a CSV / Excel / JSONL file and ingest all rows."""
        try:
            if filename.endswith(".jsonl") or filename.endswith(".json"):
                import json as _json
                rows = [
                    _json.loads(line)
                    for line in file_content.decode("utf-8").splitlines()
                    if line.strip()
                ]
                # Map 'date' → 'shift_date' for JSONL; keep everything else as-is
                for r in rows:
                    if "date" in r and "shift_date" not in r:
                        r["shift_date"] = r.pop("date")
            elif filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(file_content), index_col=0)
                df.rename(columns=COLUMN_MAP, inplace=True)
                df.columns = [c.strip() for c in df.columns]
                rows = df.to_dict(orient="records")
            elif filename.endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(file_content), index_col=0)
                df.rename(columns=COLUMN_MAP, inplace=True)
                df.columns = [c.strip() for c in df.columns]
                rows = df.to_dict(orient="records")
            else:
                raise ValueError(f"Unsupported file type: {filename}")
        except Exception as e:
            logger.error(f"Failed to parse file {filename}: {e}")
            raise

        results = []
        for row in rows:
            result = await self._ingest_row(row, db, ocr_confidence)
            results.append(result)

        await db.commit()
        logger.info(f"Ingested {len(results)} reports from {filename}")
        return {
            "total": len(results),
            "processable": sum(1 for r in results if r["ingest_status"] == IngestStatus.PROCESSABLE),
            "manual_review": sum(1 for r in results if r["ingest_status"] == IngestStatus.MANUAL_REVIEW),
            "stage1_flagged": sum(1 for r in results if r.get("stage1_flagged")),
            "report_ids": [r["id"] for r in results],
        }

    async def _ingest_row(self, row: dict, db: AsyncSession, ocr_confidence: float) -> dict:
        """Process a single row dict into the full pipeline."""
        report_id = str(uuid.uuid4())
        text = str(row.get("report_text", "")).strip()

        # ── 1. OCR Gate ───────────────────────────────────────────────────────
        if not text or ocr_confidence < 0.6:
            report = Report(
                id=report_id,
                report_text=text or "[EMPTY]",
                ocr_confidence=ocr_confidence,
                ingest_status=IngestStatus.MANUAL_REVIEW,
                has_site_metadata=False,
                has_equipment_metadata=False,
                has_shift_metadata=False,
                text_only_mode=True,
                lower_confidence_flag=True,
            )
            db.add(report)
            self._add_audit(db, report_id, "INGESTED", metadata={
                "routing_reason": RoutingReason.OCR_FAILED,
                "ocr_confidence": ocr_confidence,
            })
            return {"id": report_id, "ingest_status": IngestStatus.MANUAL_REVIEW}

        # ── 2. Metadata Completeness Check → Graceful Degradation ─────────────
        has_site  = bool(row.get("site"))
        # Accept equipment from new JSONL field or legacy industry_sector
        has_equip = bool(row.get("equipment_type") or row.get("industry_sector") or row.get("equipment"))
        has_shift = bool(row.get("shift_date"))
        text_only = not (has_site and has_equip and has_shift)
        lower_conf_flag = text_only

        routing_reason_meta = RoutingReason.MISSING_METADATA if text_only else None

        # ── 3. Parse shift date ────────────────────────────────────────────────
        shift_dt = None
        if row.get("shift_date"):
            try:
                shift_dt = pd.to_datetime(row["shift_date"]).to_pydatetime()
            except Exception:
                pass

        # ── 4. Derive / read hi_po ────────────────────────────────────────────
        # Priority 1: pre-labelled hi_po from new synthetic JSONL
        # Priority 2: derive from legacy Potential Accident Level codes
        if row.get("hi_po") is not None:
            hi_po = bool(row["hi_po"])
        else:
            pot_level = str(row.get("potential_accident_level", "")).strip()
            hi_po = pot_level in HIPO_LEVELS

        # Legacy field preserved for DB storage (None for new JSONL data)
        pot_level = str(row.get("potential_accident_level", "")).strip()

        # ── 5. Save Report ────────────────────────────────────────────────────
        report = Report(
            id=report_id,
            site=row.get("site"),
            country=row.get("country"),
            # Map equipment_type (JSONL) → industry_sector (DB column)
            industry_sector=row.get("industry_sector") or row.get("equipment_type"),
            shift_date=shift_dt,
            reporter_role=row.get("reporter_role"),
            report_text=text,
            # Map cause_category (JSONL) → critical_risk (DB column) as fallback
            critical_risk=row.get("critical_risk") or row.get("cause_category"),
            ocr_confidence=ocr_confidence,
            ingest_status=IngestStatus.PROCESSABLE,
            has_site_metadata=has_site,
            has_equipment_metadata=has_equip,
            has_shift_metadata=has_shift,
            text_only_mode=text_only,
            lower_confidence_flag=lower_conf_flag,
        )
        db.add(report)

        # ── 6. Domain Feature Extraction ─────────────────────────────────────
        feat_result = extractor.extract(text)
        fv = FeatureVector(
            report_id=report_id,
            energy_types=feat_result.energy_types,
            barrier_phrases=feat_result.barrier_phrases,
            barrier_status=feat_result.barrier_status,
            has_energy_signal=feat_result.has_energy_signal,
            has_barrier_failure=feat_result.has_barrier_failure,
            hazard_categories=feat_result.hazard_categories,
            safety_mgmt_terms=feat_result.safety_mgmt_terms,
            equipment_terms=feat_result.equipment_terms,
            interlock_bypass_detected=feat_result.interlock_bypass_detected,
            hi_po=hi_po,
            accident_level=str(row.get("accident_level", "")).strip() or None,
            potential_accident_level=pot_level or None,
        )
        db.add(fv)

        # ── 7. Stage 1 Filter (inline / synchronous) ──────────────────────────
        s1 = stage1_filter.predict(text, feat_result)

        routing = RoutingReason.NONE
        if text_only:
            routing = RoutingReason.MISSING_METADATA

        # Three-way operational state
        if s1.flagged:
            op_state = "FLAGGED"
        else:
            op_state = "NON_SIF"

        pred = Prediction(
            report_id=report_id,
            stage1_flagged=s1.flagged,
            stage1_score=s1.score,
            routing_reason=routing,
            operational_state=op_state,
            confidence_band=ConfidenceBand.LOW if lower_conf_flag else None,
        )
        db.add(pred)

        # ── 8. Audit log entry ────────────────────────────────────────────────
        self._add_audit(db, report_id, "INGESTED", metadata={
            "stage1_flagged": s1.flagged,
            "stage1_score": round(s1.score, 4),
            "rule_triggered": s1.rule_triggered,
            "text_only_mode": text_only,
            "hi_po": hi_po,
        })

        return {
            "id": report_id,
            "ingest_status": IngestStatus.PROCESSABLE,
            "stage1_flagged": s1.flagged,
        }

    def _add_audit(self, db: AsyncSession, report_id: str, event: str, metadata: dict):
        entry = AuditLog(
            report_id=report_id,
            event_type=event,
            metadata_json=metadata,
        )
        db.add(entry)


# Singleton
ingestion_service = IngestionService()
