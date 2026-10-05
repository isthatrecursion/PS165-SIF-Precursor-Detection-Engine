"""
SQLAlchemy ORM Models — Full SIH165 Schema

Tables:
  reports            — raw ingested safety report records
  features           — domain feature vectors extracted per report
  predictions        — model outputs (Stage 1 + Stage 2)
  officer_decisions  — human validation decisions (agree/disagree)
  audit_log          — immutable append-only ledger of all decisions
  active_learning_queue — reports queued for human relabeling
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Enumerations ──────────────────────────────────────────────────────────────

class IngestStatus:
    PROCESSABLE   = "PROCESSABLE"
    MANUAL_REVIEW = "MANUAL_REVIEW"   # OCR failed or other quality issue

class RoutingReason:
    OCR_FAILED       = "OCR_FAILED"
    LOW_CONFIDENCE   = "LOW_CONFIDENCE"
    AMBIGUOUS_OOD    = "AMBIGUOUS_OOD"
    MISSING_METADATA = "MISSING_METADATA"
    NONE             = None

class ConfidenceBand:
    HIGH      = "HIGH"
    LOW       = "LOW"
    AMBIGUOUS = "AMBIGUOUS"
    OOD       = "OOD"

class DecisionType:
    AGREE    = "AGREE"
    DISAGREE = "DISAGREE"

class BarrierStatus:
    PRESENT      = "PRESENT"
    MISSING      = "MISSING"
    FAILED       = "FAILED"
    BYPASSED     = "BYPASSED"
    NOT_VERIFIED = "NOT_VERIFIED"
    UNKNOWN      = "UNKNOWN"


# ── Reports ───────────────────────────────────────────────────────────────────

class Report(Base):
    __tablename__ = "reports"

    id               = Column(String, primary_key=True, default=_uuid)
    # Source metadata
    source_file      = Column(String, nullable=True)
    site             = Column(String, nullable=True)       # Local_01 etc.
    country          = Column(String, nullable=True)
    industry_sector  = Column(String, nullable=True)
    equipment        = Column(String, nullable=True)
    shift_date       = Column(DateTime, nullable=True)
    reporter_role    = Column(String, nullable=True)       # "Employee" / "Third Party" etc.
    # Report content
    report_text      = Column(Text, nullable=False)
    report_type      = Column(String, nullable=True)       # Unsafe Act / Condition / Near Miss
    critical_risk    = Column(String, nullable=True)       # raw dataset column
    # Quality gate
    ocr_confidence   = Column(Float, nullable=True, default=1.0)
    ingest_status    = Column(String, nullable=False, default=IngestStatus.PROCESSABLE)
    # Metadata completeness
    has_site_metadata      = Column(Boolean, nullable=False, default=True)
    has_equipment_metadata = Column(Boolean, nullable=False, default=True)
    has_shift_metadata     = Column(Boolean, nullable=False, default=True)
    text_only_mode         = Column(Boolean, nullable=False, default=False)
    lower_confidence_flag  = Column(Boolean, nullable=False, default=False)
    # Audit
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    features    = relationship("FeatureVector", back_populates="report", uselist=False)
    prediction  = relationship("Prediction",    back_populates="report", uselist=False)
    decision    = relationship("OfficerDecision", back_populates="report", uselist=False)


# ── Feature Vectors ───────────────────────────────────────────────────────────

class FeatureVector(Base):
    __tablename__ = "features"

    id        = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, unique=True, index=True)

    # A. Energy features (comma-separated detected types)
    energy_types     = Column(JSON, nullable=True)   # ["electrical", "pressure", ...]
    # B. Barrier status
    barrier_phrases  = Column(JSON, nullable=True)   # ["not isolated", "no permit", ...]
    barrier_status   = Column(String, nullable=True) # BarrierStatus enum value
    # C. Hazard category
    hazard_categories = Column(JSON, nullable=True)  # ["electrical", "chemical", ...]
    # D. Safety management terms
    safety_mgmt_terms = Column(JSON, nullable=True)  # ["LOTO", "JSA", "work permit", ...]
    # E. Equipment / control terms
    equipment_terms   = Column(JSON, nullable=True)  # ["PSV", "gas detector", ...]
    # Interlock bypass (high-value signal, Section 10)
    interlock_bypass_detected = Column(Boolean, nullable=False, default=False)
    # Composite flags
    has_energy_signal  = Column(Boolean, nullable=False, default=False)
    has_barrier_failure = Column(Boolean, nullable=False, default=False)
    # Hi-Po indicator (derived from Potential Accident Level)
    hi_po             = Column(Boolean, nullable=True)
    # Original severity fields from dataset (for labeling)
    accident_level          = Column(String, nullable=True)  # I–V
    potential_accident_level = Column(String, nullable=True)  # I–VI

    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="features")


# ── Predictions ───────────────────────────────────────────────────────────────

class Prediction(Base):
    __tablename__ = "predictions"

    id        = Column(String, primary_key=True, default=_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False, unique=True, index=True)

    # Stage 1
    stage1_flagged  = Column(Boolean, nullable=True)
    stage1_score    = Column(Float,   nullable=True)

    # Stage 2 — core outputs
    sif_flag        = Column(Boolean, nullable=True)
    calibrated_prob = Column(Float,   nullable=True)   # 0.0–1.0
    confidence_band = Column(String,  nullable=True)   # ConfidenceBand enum
    ood_score       = Column(Float,   nullable=True)   # Mahalanobis distance

    # Multi-label outputs
    iogp_rules      = Column(JSON, nullable=True)      # ["Energy Isolation", ...]
    cause_categories = Column(JSON, nullable=True)     # ["Violation of WPS", ...]

    # Explainability payloads
    shap_values     = Column(JSON, nullable=True)      # {feature: float, ...}
    ig_spans        = Column(JSON, nullable=True)      # [{start,end,text,score}, ...]

    # Routing
    routing_reason  = Column(String, nullable=True)    # RoutingReason or None
    # Three-way operational state: FLAGGED / NON_SIF / NEEDS_REVIEW
    operational_state = Column(String, nullable=True)

    created_at      = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="prediction")


# ── Officer Decisions ─────────────────────────────────────────────────────────

class OfficerDecision(Base):
    __tablename__ = "officer_decisions"

    id          = Column(String, primary_key=True, default=_uuid)
    report_id   = Column(String, ForeignKey("reports.id"), nullable=False, unique=True, index=True)
    officer_id  = Column(String, nullable=False)           # anonymized officer ref
    officer_role = Column(String, nullable=True)
    decision    = Column(String, nullable=False)           # DecisionType
    notes       = Column(Text,   nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    report = relationship("Report", back_populates="decision")


# ── Audit Log (immutable append-only) ────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_log"

    id              = Column(String, primary_key=True, default=_uuid)
    report_id       = Column(String, nullable=False, index=True)
    event_type      = Column(String, nullable=False)   # INGESTED / PREDICTED / DECIDED
    model_score     = Column(Float,  nullable=True)
    officer_action  = Column(String, nullable=True)
    officer_role    = Column(String, nullable=True)
    metadata_json   = Column(JSON,   nullable=True)
    timestamp       = Column(DateTime, default=datetime.utcnow, nullable=False)


# ── Active Learning Queue ─────────────────────────────────────────────────────

class ActiveLearningQueue(Base):
    __tablename__ = "active_learning_queue"

    id              = Column(String, primary_key=True, default=_uuid)
    report_id       = Column(String, ForeignKey("reports.id"), nullable=False, index=True)
    model_prob      = Column(Float,  nullable=True)
    queue_reason    = Column(String, nullable=True)    # "LOW_CONFIDENCE" / "OFFICER_DISAGREE"
    corrected_sif   = Column(Boolean, nullable=True)  # label after human correction
    corrected_iogp  = Column(JSON,   nullable=True)
    corrected_cause = Column(JSON,   nullable=True)
    labeled_by      = Column(String, nullable=True)
    labeled_at      = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    status          = Column(String, nullable=False, default="PENDING")  # PENDING / LABELED
