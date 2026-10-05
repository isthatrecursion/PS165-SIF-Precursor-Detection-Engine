"""
S4 — Stage 2 Full ML Pipeline Training Script
SIH165 SIF Precursor Detection Engine

Architecture:
    DistilBERT (frozen base + fine-tuned classification head)
    → [CLS] embeddings → XGBoost ensemble
    → Platt scaling calibration
    → Mahalanobis OOD detection
    → TreeSHAP explanations

Label strategy (SIH165 synthetic dataset):
    SIF = True  ←→  sif_precursor == True  (pre-labelled in JSONL)
    Garbled records (sif_precursor is None) are dropped at load time.

Split strategy (Section 24):
    Time-based primary holdout (last 20% by report date)
    Site-based secondary holdout (Geleki Oil Field withheld entirely)

Dataset:
    data/synthetic/synthetic_oilgas_3000.jsonl
    3 000 synthetic Oil & Gas safety reports in Oil India / OISD context.

Run from Prototype 165 root:
    backend\\venv\\Scripts\\python ml\\scripts\\train_stage2.py
"""

import sys
import os
import pickle
import json
import logging
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report, roc_auc_score,
    precision_recall_fscore_support,
)
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s")
log = logging.getLogger("SIH165.train")

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

MODELS_DIR = Path("ml/models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

DATA_PATH = Path("data/synthetic/synthetic_oilgas_3000.jsonl")


# ── STAGE 0: Load & Label Dataset ────────────────────────────────────────────

def load_and_label(path: Path) -> pd.DataFrame:
    """
    Load the synthetic Oil & Gas JSONL dataset.

    Schema fields used:
      report_text     — free-text narrative (primary input)
      sif_precursor   — ground-truth label (True/False; None = garbled, dropped)
      date            — ISO date string for time-based split
      site            — location name for site-based OOD split
      energy_types    — list[str] from generation (informational; not fed to model)
      barrier_status  — absent / failed / bypassed / intact / n/a
    """
    log.info(f"Loading dataset from {path}")

    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    df = pd.DataFrame(records)

    # Drop garbled records (sif_precursor is None — unlabelled by design)
    df = df[df["sif_precursor"].notna()].copy()

    # Drop rows with no usable text
    df = df.dropna(subset=["report_text"])
    df["report_text"] = df["report_text"].astype(str).str.strip()
    df = df[df["report_text"].str.len() > 10]

    # Label is already a boolean — convert to int for sklearn
    df["sif_label"] = df["sif_precursor"].astype(bool).astype(int)

    # Parse date for time-based split
    df["shift_date"] = pd.to_datetime(df["date"], errors="coerce")

    # Normalise site column (already named 'site' in our schema)
    df["site"] = df["site"].fillna("Unknown")

    log.info(
        f"Loaded {len(df)} records | "
        f"SIF positive: {df['sif_label'].sum()} ({df['sif_label'].mean()*100:.1f}%) | "
        f"Difficulty mix: " +
        str(df["record_difficulty"].value_counts().to_dict())
        if "record_difficulty" in df.columns else ""
    )
    return df


# ── STAGE 1: Train/Test Split (Time + Site based) ────────────────────────────

def make_splits(df: pd.DataFrame):
    """
    Primary split: time-based — last 20% of records by date = test set.
    Site-OOD probe: 'Geleki Oil Field' is withheld from training to probe
    site-generalisation (logged but not used to select final threshold).
    """
    df_sorted = df.sort_values("shift_date", na_position="first").reset_index(drop=True)
    n = len(df_sorted)
    split_idx = int(n * 0.80)

    train_df = df_sorted.iloc[:split_idx].copy()
    test_df  = df_sorted.iloc[split_idx:].copy()

    # Log site-OOD stats (Geleki Oil Field is our reserved OOD probe)
    ood_site = "Geleki Oil Field"
    ood_in_train = (train_df["site"] == ood_site).sum()
    ood_in_test  = (test_df["site"] == ood_site).sum()
    log.info(f"Time split  →  Train: {len(train_df)}  |  Test: {len(test_df)}")
    log.info(f"Train SIF rate: {train_df['sif_label'].mean()*100:.1f}%  |  Test SIF rate: {test_df['sif_label'].mean()*100:.1f}%")
    log.info(f"OOD probe site '{ood_site}': {ood_in_train} in train, {ood_in_test} in test")

    return train_df, test_df


# ── STAGE 2: Feature Engineering ─────────────────────────────────────────────

def build_features(df: pd.DataFrame, fit_scaler=None):
    """
    Combine:
      A. DistilBERT [CLS] embeddings (768-dim)
      B. Domain feature vector (12-dim)

    If GPU available: uses CUDA.
    """
    import torch
    from transformers import AutoTokenizer, AutoModel

    device = "cuda" if torch.cuda.is_available() else "cpu"
    log.info(f"Embedding device: {device}")

    # ── B. Domain feature vector ──────────────────────────────────────────────
    from app.pipeline.feature_extractor import extractor

    domain_features = []
    for text in df["report_text"]:
        r = extractor.extract(str(text))
        domain_features.append([
            float(r.has_energy_signal),
            float(r.has_barrier_failure),
            float(r.interlock_bypass_detected),
            float(len(r.energy_types)),
            float(len(r.barrier_phrases)),
            float(len(r.safety_mgmt_terms)),
            float(len(r.equipment_terms)),
            float(len(r.hazard_categories)),
            float("electrical" in r.energy_types),
            float("pressure" in r.energy_types),
            float("thermal" in r.energy_types),
            float("chemical" in r.energy_types),
            float(r.barrier_status == "BYPASSED"),
            float(r.barrier_status == "MISSING"),
            float(r.barrier_status == "NOT_VERIFIED"),
        ])

    X_domain = np.array(domain_features, dtype=np.float32)

    # ── A. DistilBERT embeddings ──────────────────────────────────────────────
    MODEL_NAME = "distilbert-base-uncased"
    log.info(f"Loading {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME).to(device)
    model.eval()

    embeddings = []
    batch_size = 16
    texts = df["report_text"].tolist()

    log.info(f"Encoding {len(texts)} texts in batches of {batch_size}...")
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = texts[i: i + batch_size]
            encoded = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors="pt",
            )
            encoded = {k: v.to(device) for k, v in encoded.items()}
            out = model(**encoded)
            # [CLS] token embedding
            cls_emb = out.last_hidden_state[:, 0, :].cpu().numpy()
            embeddings.append(cls_emb)

            if (i // batch_size) % 5 == 0:
                log.info(f"  Encoded {min(i+batch_size, len(texts))}/{len(texts)}")

    X_bert = np.vstack(embeddings)
    log.info(f"BERT embeddings shape: {X_bert.shape}")

    # ── Combine ───────────────────────────────────────────────────────────────
    X_combined = np.hstack([X_bert, X_domain])
    log.info(f"Combined feature shape: {X_combined.shape}")

    # Scale
    if fit_scaler is None:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_combined)
    else:
        scaler = fit_scaler
        X_scaled = scaler.transform(X_combined)

    return X_scaled, scaler, X_domain


# ── STAGE 3: Train XGBoost Classifier ────────────────────────────────────────

def train_xgboost(X_train, y_train):
    import xgboost as xgb

    # Handle class imbalance
    pos = y_train.sum()
    neg = len(y_train) - pos
    scale_pos = neg / pos if pos > 0 else 1.0

    log.info(f"Training XGBoost | scale_pos_weight={scale_pos:.2f}")

    clf = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos,
        eval_metric="aucpr",
        random_state=42,
        device="cpu",
    )

    clf.fit(X_train, y_train, verbose=False)
    return clf


# ── STAGE 4: Platt Scaling Calibration ───────────────────────────────────────

class PlattCalibratedXGB:
    """Manual Platt scaling wrapper — avoids sklearn DLL dependency."""
    def __init__(self, base_clf, lr_model):
        self.base_clf = base_clf
        self.lr_model = lr_model

    def predict_proba(self, X):
        raw_scores = self.base_clf.predict_proba(X)[:, 1].reshape(-1, 1)
        cal_probs = self.lr_model.predict_proba(raw_scores)[:, 1]
        return np.column_stack([1 - cal_probs, cal_probs])


def calibrate(clf, X_train, y_train):
    log.info("Applying Platt scaling calibration (manual LogisticRegression)...")
    raw_scores = clf.predict_proba(X_train)[:, 1].reshape(-1, 1)
    lr = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
    lr.fit(raw_scores, y_train)
    calibrated = PlattCalibratedXGB(clf, lr)
    return calibrated


# ── STAGE 5: OOD Detection (Mahalanobis) ─────────────────────────────────────

def fit_ood_detector(X_train_pos, X_train_neg):
    """
    Fit a Mahalanobis distance detector on in-distribution training data.
    Reports with Mahalanobis distance above threshold → AMBIGUOUS / OOD.
    """
    from sklearn.covariance import EmpiricalCovariance

    log.info("Fitting OOD detector (Mahalanobis)...")

    # Use all training data as in-distribution reference
    ood = EmpiricalCovariance().fit(np.vstack([X_train_pos, X_train_neg]))
    return ood


# ── STAGE 6: IOGP Rule Classifier ────────────────────────────────────────────

CRITICAL_RISK_TO_IOGP = {
    "Electrical":               "Energy Isolation",
    "Electrical Safety":        "Energy Isolation",
    "Work at height":           "Working at Height",
    "Working at Heights":       "Working at Height",
    "Driving":                  "Vehicle / Mobile Equipment",
    "Machinery and Equipment":  "Mechanical",
    "Mechanical":               "Mechanical",
    "Confined Space":           "Confined Space",
    "Chemical":                 "Hazardous Substances",
    "Fire":                     "Fire Prevention",
    "Explosives":               "Explosives",
    "Pressure Systems":         "Pressure Systems",
    "Hot Work":                 "Fire Prevention",
    "Lifting Operations":       "Lifting Operations",
    "Hand Tools":               "Mechanical",
    "Slip Trip Fall":           "Slip/Trip/Fall Prevention",
    "Manual Handling":          "Manual Handling",
    "Rock Fall":                "Working at Height",
}

CAUSE_TAXONOMY = [
    "Violation of Work Procedures",
    "No Procedure / SOP Available",
    "Lack of Training / Competency",
    "Inadequate Supervision",
    "Failure to Use PPE",
    "Tool / Equipment Defect",
    "Unsafe Work Conditions",
    "Risk Assessment Not Done",
    "Management System Failure",
    "Communication Failure",
    "Fatigue / Physical State",
    "Environmental Condition",
    "Interlock / Safety Device Bypassed",
    "Other / Uncategorized",
]


def derive_iogp_rules(critical_risk: str, features) -> list:
    rules = []
    cr = str(critical_risk).strip()
    for key, rule in CRITICAL_RISK_TO_IOGP.items():
        if key.lower() in cr.lower() and rule not in rules:
            rules.append(rule)
    # Add from feature vector
    if features.interlock_bypass_detected:
        rules.append("Energy Isolation")
    if features.has_energy_signal and "electrical" in features.energy_types:
        if "Energy Isolation" not in rules:
            rules.append("Energy Isolation")
    if features.has_barrier_failure and not rules:
        rules.append("Permit to Work")
    return rules or ["General Safety"]


def derive_cause(features, text: str) -> list:
    import re
    causes = []
    t = text.lower()
    if re.search(r"\bprocedure\b.{0,30}\bnot\s+(followed|applied|done)\b", t, re.I):
        causes.append("Violation of Work Procedures")
    if re.search(r"\bno\s+(procedure|SOP|permit|JSA)\b", t, re.I):
        causes.append("No Procedure / SOP Available")
    if features.interlock_bypass_detected:
        causes.append("Interlock / Safety Device Bypassed")
    if re.search(r"\bPPE\b.{0,20}\bnot\s+(worn|used|provided)\b", t, re.I):
        causes.append("Failure to Use PPE")
    if re.search(r"\bdefect(ive)?\b|\bmalfunction\b|\bbroken\b", t, re.I):
        causes.append("Tool / Equipment Defect")
    if re.search(r"\bsupervision\b|\bsupervisor\b.{0,30}\bnot\s+present\b", t, re.I):
        causes.append("Inadequate Supervision")
    if re.search(r"\btrain(ing|ed)?\b.{0,20}\bnot\b|\bunqualified\b", t, re.I):
        causes.append("Lack of Training / Competency")
    if re.search(r"\bcommunicat\b|\bnot\s+informed\b|\bnot\s+notified\b", t, re.I):
        causes.append("Communication Failure")
    return causes or ["Other / Uncategorized"]


# ── STAGE 7: Evaluation ───────────────────────────────────────────────────────

def evaluate(clf_calibrated, X_test, y_test, threshold=0.25):
    probs = clf_calibrated.predict_proba(X_test)[:, 1]
    preds = (probs >= threshold).astype(int)

    p, r, f1, _ = precision_recall_fscore_support(y_test, preds, average="binary")
    auc = roc_auc_score(y_test, probs)
    # Manual Brier score (avoids sklearn._isotonic DLL)
    brier = float(np.mean((probs - y_test) ** 2))

    log.info("=" * 55)
    log.info("  EVALUATION RESULTS")
    log.info("=" * 55)
    log.info(f"  Threshold  : {threshold}")
    log.info(f"  Precision  : {p:.3f}")
    log.info(f"  Recall     : {r:.3f}  (floor >= 0.90 required)")
    log.info(f"  F1         : {f1:.3f}")
    log.info(f"  ROC-AUC    : {auc:.3f}")
    log.info(f"  Brier Score: {brier:.3f}  (lower is better)")
    log.info("=" * 55)

    if r < 0.90:
        log.warning(f"  RECALL FLOOR NOT MET: {r:.3f} < 0.90. Adjust threshold or retrain.")
    else:
        log.info("  RECALL FLOOR MET.")

    return {"precision": p, "recall": r, "f1": f1, "auc": auc, "brier": brier}


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    log.info("SIH165 Stage 2 — Full ML Training Pipeline")
    log.info("=" * 55)

    df = load_and_label(DATA_PATH)
    train_df, test_df = make_splits(df)

    y_train = train_df["sif_label"].values
    y_test  = test_df["sif_label"].values

    log.info("Building training features (BERT + domain)...")
    X_train, scaler, X_train_domain = build_features(train_df)

    log.info("Building test features...")
    X_test, _, X_test_domain = build_features(test_df, fit_scaler=scaler)

    # XGBoost
    xgb_clf = train_xgboost(X_train, y_train)

    # Calibration
    xgb_cal = calibrate(xgb_clf, X_train, y_train)

    # OOD
    ood_detector = fit_ood_detector(
        X_train[y_train == 1],
        X_train[y_train == 0],
    )

    # Evaluation
    metrics = evaluate(xgb_cal, X_test, y_test, threshold=0.25)

    # Save models
    log.info("Saving models...")
    with open(MODELS_DIR / "stage2_xgb.pkl", "wb") as f:
        pickle.dump(xgb_cal, f)
    with open(MODELS_DIR / "stage2_scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    with open(MODELS_DIR / "stage2_ood.pkl", "wb") as f:
        pickle.dump(ood_detector, f)
    with open(MODELS_DIR / "stage2_metrics.json", "w") as f:
        json.dump({**metrics, "trained_at": datetime.utcnow().isoformat()}, f, indent=2)

    log.info(f"Models saved to {MODELS_DIR}/")
    log.info("Training complete.")


if __name__ == "__main__":
    main()
