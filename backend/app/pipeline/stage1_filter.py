"""
Stage 1 — High-Recall Filter (S3)

Architecture:
    TF-IDF vectorizer  +  Logistic Regression  +  Lexicon override rules

Design constraints:
  - Target recall: near-100% (deliberately over-flags; ~30-40% pass rate)
  - Runs inline / synchronously at ingestion time
  - CPU-only (no GPU required)
  - Hard lexicon override: if interlock_bypass OR
    (has_energy_signal AND has_barrier_failure) → always flag

Two operational modes:
  1. TRAINED: loads saved TF-IDF + LogReg from disk (production)
  2. HEURISTIC: pure rule-based fallback before model is trained (bootstrap)
"""
import os
import pickle
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.pipeline.feature_extractor import FeatureExtractionResult, extractor
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Stage1Result:
    flagged: bool
    score: float          # raw logistic regression probability (or heuristic score)
    rule_triggered: bool  # True if lexicon override forced the flag


class Stage1Filter:
    """
    Stage 1 High-Recall Filter.

    Call predict() for a single report.
    Falls back to heuristic mode if trained models are not yet available.
    """

    def __init__(self):
        self._tfidf  = None
        self._logreg = None
        self._loaded = False
        self._try_load_models()

    # ── Model Loading ─────────────────────────────────────────────────────────

    def _try_load_models(self):
        tfidf_path  = settings.stage1_tfidf_path
        logreg_path = settings.stage1_logreg_path
        if os.path.exists(tfidf_path) and os.path.exists(logreg_path):
            try:
                with open(tfidf_path, "rb") as f:
                    self._tfidf = pickle.load(f)
                with open(logreg_path, "rb") as f:
                    self._logreg = pickle.load(f)
                self._loaded = True
                logger.info("Stage 1: trained models loaded successfully.")
            except Exception as e:
                logger.warning(f"Stage 1: failed to load models ({e}). Using heuristic mode.")
        else:
            logger.info("Stage 1: model files not found. Using heuristic (rule-based) mode.")

    def reload(self):
        """Hot-reload models from disk (call after retraining)."""
        self._loaded = False
        self._tfidf  = None
        self._logreg = None
        self._try_load_models()

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(
        self,
        report_text: str,
        features: Optional[FeatureExtractionResult] = None,
    ) -> Stage1Result:
        """
        Returns Stage1Result with flagged=True if the report should proceed
        to Stage 2 for full precision classification.

        Lexicon override rules (Section 10 + Section 2 of consolidated doc):
          • interlock bypass detected → always flag
          • has_energy_signal AND has_barrier_failure → always flag
        """
        if features is None:
            features = extractor.extract(report_text)

        # ── Hard lexicon override (highest priority) ────────────────────────
        rule_triggered = False
        if features.interlock_bypass_detected:
            rule_triggered = True
        elif features.has_energy_signal and features.has_barrier_failure:
            rule_triggered = True

        if rule_triggered:
            return Stage1Result(flagged=True, score=1.0, rule_triggered=True)

        # ── Trained ML path ────────────────────────────────────────────────
        if self._loaded:
            return self._ml_predict(report_text, features)

        # ── Heuristic fallback ─────────────────────────────────────────────
        return self._heuristic_predict(features)

    def _ml_predict(self, text: str, features: FeatureExtractionResult) -> Stage1Result:
        """TF-IDF + LogReg prediction with a low threshold to maximize recall."""
        try:
            tfidf_vec = self._tfidf.transform([text])
            prob = self._logreg.predict_proba(tfidf_vec)[0][1]
            # Use a low threshold (0.25) to prioritize recall over precision
            threshold = 0.25
            flagged = (prob >= threshold) or features.has_energy_signal
            return Stage1Result(flagged=flagged, score=float(prob), rule_triggered=False)
        except Exception as e:
            logger.warning(f"Stage 1 ML predict failed: {e}. Falling back to heuristic.")
            return self._heuristic_predict(features)

    def _heuristic_predict(self, features: FeatureExtractionResult) -> Stage1Result:
        """
        Rule-based heuristic — used before training or as fallback.

        Scoring:
          +0.4  for any energy signal
          +0.4  for any barrier failure phrase
          +0.2  for each safety management term missed (JSA, permit, etc.)
          Flag if score >= 0.3  (very low threshold → near-100% recall)
        """
        score = 0.0
        if features.has_energy_signal:
            score += 0.4
        if features.has_barrier_failure:
            score += 0.4
        if features.safety_mgmt_terms:
            score += 0.1 * min(len(features.safety_mgmt_terms), 2)
        if features.equipment_terms:
            score += 0.1

        flagged = score >= 0.3
        return Stage1Result(flagged=flagged, score=min(score, 1.0), rule_triggered=False)


# Singleton — loaded once at startup
stage1_filter = Stage1Filter()
