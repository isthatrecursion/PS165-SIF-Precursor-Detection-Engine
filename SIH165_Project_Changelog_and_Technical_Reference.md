# SIH165 — Complete Project Changelog & Technical Reference

> **Document purpose:** Captures every technical change, design decision, and implementation
> detail made during the development of this prototype. This is complementary to
> `SIH165_Consolidated_Project_Information_Finalv1.md` (domain theory) and
> `Final System Architecture 165.md` (architecture diagram).

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Synthetic Dataset](#2-synthetic-dataset)
3. [Backend Implementation](#3-backend-implementation)
4. [ML Pipeline](#4-ml-pipeline)
5. [Frontend Implementation](#5-frontend-implementation)
6. [Problem Statement Audit & Gap Closure](#6-problem-statement-audit--gap-closure)
7. [Bug Fixes](#7-bug-fixes)
8. [Multilingual Consideration](#8-multilingual-consideration-hindi--assamese)
9. [File Inventory](#9-complete-file-inventory)
10. [How to Run](#10-how-to-run)
11. [Known Limitations & Future Work](#11-known-limitations--future-work)

---

## 1. Project Overview

| Field | Value |
|---|---|
| **Problem Statement** | AI/NLP Engine to Detect SIF Precursors in OIL's UA/UC and Near-Miss Reports |
| **Hackathon** | Smart India Hackathon (SIH) 2024 — Problem ID SIH165 |
| **Target Org** | Oil India Limited (OIL) |
| **Tech Stack** | Python 3.12 · FastAPI · SQLAlchemy (async SQLite) · DistilBERT · XGBoost · React 18 · Vite · Recharts |
| **Architecture** | Two-stage NLP pipeline (high-recall filter → precision classifier) + officer-facing triage UI + leadership analytics dashboard |

### Core Requirement Mapping

| PS Requirement | Implementation |
|---|---|
| a) Classify SIF-potential vs non-SIF | ✅ Two-stage pipeline (Stage 1 TF-IDF + Stage 2 DistilBERT+XGBoost) |
| b) Tag to IOGP Life-Saving Rules | ✅ Multi-label `_derive_iogp()` with 12+ rule mappings |
| c) Surface recurring precursor patterns | ✅ Dashboard with site cards, IOGP frequency, cause distribution, activity density, site×activity cross-tab, monthly trend |
| d) Interactive dashboard ranking sites/activities | ✅ Leadership Analytics Dashboard with 5 panels |
| e) Auto-map to Life-Saving Rules | ✅ Automatic per-report, aggregated on dashboard |

---

## 2. Synthetic Dataset

### Why Synthetic Data

OIL's real UA/UC and near-miss reports are not publicly available. The dataset is a **proof-of-concept substrate** — not a production training set. This is stated openly in the system.

### Generation Process

- **Generator script:** `data/synthetic/generate_dataset.py` (53 KB, ~1,100 lines)
- **Batched output:** 6 batches of 500 reports each → compiled into `synthetic_oilgas_3000.jsonl` (2.26 MB, 3,000 records)
- **Oil India framing:** Sites use OIL locations (Digboi Refinery, Lakwa Gas Plant, Geleki Oil Field, Duliajan HQ, Moran Oil Field, Numaligarh Refinery, Tengakhat Drilling Site)
- **Equipment:** BOP, wellhead, separator, LPG carousel, mud pump, gas flare stack, pipeline valve, wireline unit

### Dataset Schema (JSONL)

```json
{
  "report_text": "During routine maintenance at Lakwa Gas Plant...",
  "sif_precursor": true,
  "date": "2024-03-15",
  "site": "Lakwa Gas Plant",
  "hi_po": true,
  "critical_risk": "pressure",
  "equipment_type": "separator",
  "shift": "night"
}
```

### Difficulty Spectrum (7 categories)

| Category | Description | % of Dataset |
|---|---|---|
| Clear Positive | Energy + barrier failure, obviously dangerous | ~15% |
| Hard Positive | Subtle energy signals, implicit barrier failure | ~10% |
| Clear Negative | Housekeeping, documentation, no energy | ~30% |
| Hard Negative | Alarming language but no genuine energy exposure | ~10% |
| Ambiguous | Could go either way — border cases | ~10% |
| Garbled / Short | Poorly written, missing context | ~5% |
| Code-Mixed (Hindi/English) | Realistic OIL field personnel reports | ~3-5% |
| OOD (Out-of-Distribution) | Reports from other industries, non-safety topics | ~5% |

### Instruction Set for Generation

The generator follows a strict framing rule:

> A report is a SIF PRECURSOR if and only if it shows BOTH:
> (a) a high-energy source present, AND
> (b) a safety barrier absent, failed, bypassed, or not verified

---

## 3. Backend Implementation

### Technology

- **Framework:** FastAPI with async SQLAlchemy + aiosqlite
- **Database:** SQLite (`sih165.db`) — chosen for portability (single-file, no server setup)
- **CORS:** Enabled for `localhost:5173` (Vite dev server)

### Database Schema (6 tables)

| Table | Purpose |
|---|---|
| `reports` | Raw ingested safety report records (text, site, metadata) |
| `features` | Domain feature vectors extracted per report (energy types, barrier status, etc.) |
| `predictions` | Model outputs: Stage 1 flag + Stage 2 calibrated prob, IOGP rules, cause categories, SHAP values, IG spans |
| `officer_decisions` | Human validation decisions (AGREE / DISAGREE + notes) |
| `audit_log` | Immutable append-only ledger of all decisions |
| `active_learning_queue` | Reports queued for human relabeling (uncertainty-sampled) |

### API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/reports` | Paginated report queue with filters (site, confidence_band, stage1_flagged, sif_flag, status, iogp_rule) |
| `GET` | `/api/v1/reports/{id}` | Full report detail with predictions and XAI |
| `POST` | `/api/v1/reports/{id}/decision` | Officer submits AGREE/DISAGREE with notes |
| `GET` | `/api/v1/queue/manual-review` | Reports routed away from automated scoring |
| `POST` | `/api/v1/score/run` | Trigger Stage 2 batch scoring |
| `GET` | `/api/v1/score/status` | Scoring status counts |
| `GET` | `/api/v1/dashboard/leadership` | Aggregated leadership analytics (no individual reports) |
| `GET` | `/api/v1/dashboard/site-recall` | Per-site model recall audit |
| `GET` | `/api/v1/dashboard/activity-breakdown` | SIF density by activity type (IOGP-rule-derived) |
| `GET` | `/api/v1/dashboard/trend` | Monthly SIF precursor trend (time-series, filterable by site) |
| `GET` | `/api/v1/audit-log` | Immutable decision audit trail |
| `GET` | `/api/v1/active-learning/queue` | Uncertainty-sampled reports for relabeling |
| `POST` | `/api/v1/active-learning/{id}/label` | Submit corrected label |
| `POST` | `/api/v1/ingest` | Upload CSV/Excel/JSONL file for ingestion |

### Pipeline Modules

| Module | File | Purpose |
|---|---|---|
| Feature Extractor | `backend/app/pipeline/feature_extractor.py` | 5 feature families: Energy (9 types, 100+ regex), Barrier status, Hazard categories, Safety-management terms, Equipment/control terms, Interlock bypass detection |
| Stage 1 Filter | `backend/app/pipeline/stage1_filter.py` | TF-IDF + Logistic Regression at threshold 0.25 + hard lexicon override |
| Stage 2 Classifier | `backend/app/pipeline/stage2_classifier.py` | DistilBERT [CLS] embeddings + 15-dim domain vector → XGBoost + Platt calibration + Mahalanobis OOD detection |
| Ingestion Service | `backend/app/pipeline/ingestion_service.py` | CSV/Excel/JSONL file upload, metadata validation, OCR confidence gate, text-only mode fallback |
| Stage 2 Runner | `backend/app/pipeline/stage2_runner.py` | Batch scoring orchestration, active learning queue population |

### Key Design Decisions

1. **Stage 1 threshold at 0.25** (not 0.50) — deliberately over-flags to maximize recall; a missed SIF precursor is far worse than a false alarm
2. **Hard lexicon override:** `interlock_bypass` OR (`has_energy_signal` AND `has_barrier_failure`) → always flag regardless of ML score
3. **Never fail into false low-risk:** missing metadata → `MANUAL_REVIEW`, not `SIF=False`
4. **Three-way operational state:** `FLAGGED` / `NON_SIF` / `NEEDS_REVIEW` — OOD or missing metadata always routes to human
5. **Officer always signs off manually:** No auto-closure, no auto-escalation — the system presents evidence, the officer decides

---

## 4. ML Pipeline

### Stage 1 — High-Recall Filter

| Component | Detail |
|---|---|
| Vectorizer | TF-IDF (scikit-learn) |
| Classifier | Logistic Regression |
| Threshold | 0.25 (recall-optimized) |
| Override | Lexicon-based: bypass, energy+barrier → always flag |
| Fallback | Pure rule-based heuristic before training |

### Stage 2 — Precision Classifier

| Component | Detail |
|---|---|
| Text Encoder | `distilbert-base-uncased` (768-dim [CLS] embeddings) |
| Domain Features | 15-dimensional vector from feature extractor |
| Combined Input | 783-dimensional (768 + 15) |
| Classifier Head | XGBoost with `scale_pos_weight = 3.40` (neg/pos ratio) |
| Calibration | Platt scaling (CalibratedClassifierCV) |
| OOD Detection | Mahalanobis distance on training distribution (threshold: 3.0) |
| Training Data | 2,365 records (80% train), 592 records (20% test) |

### Trained Model Artifacts

| File | Size | Purpose |
|---|---|---|
| `ml/models/stage2_xgb.pkl` | 228 KB | XGBoost classifier + Platt calibration wrapper |
| `ml/models/stage2_scaler.pkl` | 19 KB | StandardScaler (783-dim) |
| `ml/models/stage2_ood.pkl` | 9.8 MB | Mahalanobis OOD detector |
| `ml/models/stage2_metrics.json` | 153 B | Evaluation metrics |

### Training Metrics (on synthetic data)

```json
{
  "precision": 1.0,
  "recall": 1.0,
  "f1": 1.0,
  "auc": 1.0,
  "brier": 8.35e-05,
  "trained_at": "2026-09-27T18:17:25"
}
```

> **Note:** Perfect metrics are expected on synthetic data where the generation rules are deterministic. These numbers validate the pipeline machinery, not the model's real-world generalization.

### Explainability

| Method | Layer | Output |
|---|---|---|
| TreeSHAP | Domain features (15-dim) | Per-feature contribution bar chart |
| IG Spans (regex-based) | Raw text | Character-level span highlights with label + score |
| Heuristic attribution | Fallback | Domain feature x weight products when `shap` package unavailable |

### IOGP Life-Saving Rules Covered

| Rule | Trigger Signals |
|---|---|
| Energy Isolation | `electrical`, `LOTO`, interlock bypass |
| Working at Height | `fall`, `height`, `scaffold`, `roof` |
| Confined Space | `confined space` |
| Fire Prevention / Hot Work | `fire`, `hot work`, `weld`, `spark`, `ignition` |
| Vehicle / Mobile Equipment | `vehicle`, `truck`, `forklift`, `crane`, `driving` |
| Safe Mechanical Lifting | `lifting`, `crane`, `suspended load` |
| Hazardous Substances | `chemical`, `H2S`, `toxic`, `solvent` |
| Pressure Systems | `pressure`, `PSV`, `pressurized` |
| Line of Fire | Direct match on `critical_risk` |
| SIMOPS | Concurrent operations |
| Permit to Work | Barrier failure fallback when no specific rule matches |
| General Safety | Default when no specific rule matches |

---

## 5. Frontend Implementation

### Technology

- **Framework:** React 18 + TypeScript + Vite 8
- **Charts:** Recharts (BarChart, PieChart, LineChart)
- **Icons:** Lucide React
- **Styling:** Custom CSS design system (dark mode, glassmorphism, CSS custom properties)
- **Routing:** React Router v6

### Views (7 pages)

| View | File | Purpose |
|---|---|---|
| Officer Triage Dashboard | `TriageDashboard.tsx` | Paginated, filtered report queue with stat cards showing real totals |
| Report Detail / Officer Card | `ReportDetail.tsx` | Full card: risk gauge, confidence band, IOGP tags, highlighted text, SHAP chart, officer sign-off |
| Manual Review Queue | `ManualReviewQueue.tsx` | OOD / low-confidence / missing-metadata reports needing human review |
| Leadership Analytics Dashboard | `LeadershipDashboard.tsx` | 5 panels: site cards, IOGP rule frequency, cause pie, activity density, site x activity table, monthly trend |
| Active Learning | `ActiveLearning.tsx` | Uncertainty-sampled reports for relabeling |
| Upload Reports | `IngestView.tsx` | File upload (CSV / Excel / JSONL) |
| Audit Log | `AuditLog.tsx` | Immutable decision trail |

### Key UI Components

- **ScoreGauge:** Animated SVG arc gauge showing calibrated probability (0-100%) with color-coded risk levels
- **HighlightedText:** Renders IG spans as `<mark>` elements with color coding (red = bypass/barrier, amber = energy)
- **SHAPChart:** Horizontal bar chart showing feature-level attribution (positive/negative contributions)
- **ConfBadge:** Confidence band badge (HIGH / LOW / AMBIGUOUS / OOD)
- **ProbBar:** Mini inline risk score bar with percentage

### Design System

- **Color scheme:** Dark mode with deep navy base (#0a0e1a), glassmorphic cards
- **Risk color scale:** Red (#e84855) >= 70%, Amber (#f4a823) >= 40%, Teal (#2ed8a8) < 40%
- **Typography:** Inter (sans-serif), JetBrains Mono (monospace)
- **Spacing:** 4px base unit (--space-1 through --space-10)

---

## 6. Problem Statement Audit & Gap Closure

### Initial Audit (3 gaps identified)

After building the complete system, we audited every clause of the problem statement:

| Requirement | Status Before | Gap |
|---|---|---|
| Rank activities by SIF density | Missing | No activity-type dimension |
| Surface activity patterns | Missing | No activity rollup on dashboard |
| Time trend / trending riskier | Missing | No week-over-week trend chart |

### Gap Closure (all 3 fixed)

**Gap 1 & 2 — Activity Ranking:** Added `/api/v1/dashboard/activity-breakdown` endpoint. Activity type is derived from IOGP rules (each rule maps to a hazardous activity). Dashboard now shows:
- **Activity Density bar chart** — activities ranked by SIF precursor rate, color-coded
- **Site x Activity cross-tab table** — top 15 site/activity combinations by SIF count

**Gap 3 — Time Trend:** Added `/api/v1/dashboard/trend?site=<optional>` endpoint. Dashboard now shows:
- **Monthly SIF Precursor Trend** — dual-axis line chart (SIF rate % + total reports) with a site filter dropdown

### Final Audit Score: 11/11 requirements met

---

## 7. Bug Fixes

### Triage Dashboard Filter & Count Bugs (Fixed 2026-09-29)

| Bug | Root Cause | Fix |
|---|---|---|
| **Stat cards always showed "50"** | Backend `count` returned `len(rows)` = page size, not total | Added separate `COUNT()` query returning `total_count` field |
| **SIF Flagged stat card wrong** | Frontend counted `data.reports.filter(r => r.sif_flag)` on 50-row page only | Backend now returns `sif_flagged_count` across all matching records |
| **Needs Review stat card wrong** | Same client-side counting bug | Backend now returns `needs_review_count` across all matching records |
| **Pagination "Next" never disabled** | `data.count < 50` compared page count (always 50) to 50 | Now uses `page * 50 >= data.total_count` |
| **`iogp_rule` filter not wired** | Param was declared but never added to filter list | Post-filters in Python (SQLite cannot filter JSON arrays natively) |
| **No `sif_flag` filter** | Not in original API | Added as query parameter |

### DB sif_flag Fix (2026-09-28)

- After ML re-scoring, `calibrated_prob = 0.98` but `sif_flag` stayed `NULL/False` for 564 predictions
- Root cause: Stage 2 runner computed `operational_state` correctly but did not set `sif_flag` boolean
- Fix: One-time script set `sif_flag = True` where `calibrated_prob >= 0.50 AND operational_state != "NON_SIF"`

---

## 8. Multilingual Consideration (Hindi / Assamese)

### Assessment

OIL operates in Assam (India). Field reports may be in Hindi, Assamese, or Hindi-English code-mix. We assessed how the current pipeline handles this:

| Component | English | Hindi/Assamese | Verdict |
|---|---|---|---|
| Stage 1 TF-IDF | Works | Zero vector (unknown vocab) | Fails |
| Stage 1 Lexicon override | Works | English-only regex | Fails |
| Feature Extractor | Works | English-only patterns | Fails |
| DistilBERT | English model | No Hindi/Assamese pre-training | Garbage embeddings |
| OOD Detector | — | Catches it, routes to NEEDS_REVIEW | Partial save |
| IG Spans | Works | No Hindi phrases highlighted | Fails |

### Safety Net

The Mahalanobis OOD detector catches non-English reports (high OOD score → `NEEDS_REVIEW` → routed to human). The system **never silently gives a false "non-SIF" verdict** on a language it cannot understand. But every non-English report becomes a manual queue item.

### Recommended Fix: Swap DistilBERT for MuRIL (Opted)

The user opted for **Fix 1**:

Replace `distilbert-base-uncased` with **`google/muril-base-cased`** (MuRIL — Multilingual Representations for Indian Languages). MuRIL was pre-trained on 17 Indian languages including Hindi and Assamese.

```python
# In stage2_classifier.py:
MODEL_NAME = "google/muril-base-cased"  # was "distilbert-base-uncased"
```

This requires:
1. Changing the model name constant
2. Re-running the training pipeline
3. Adding Hindi/Assamese terms to the lexicon override for the Stage 1 safety net

**Status:** Identified and opted for; not yet implemented in the codebase.

---

## 9. Complete File Inventory

### Backend (`backend/`)

```
backend/
  app/
    __init__.py
    main.py                           # FastAPI app, CORS, lifespan
    api/
      reports.py                      # Report CRUD + filters + paginated count
      dashboard.py                    # Leadership + site-recall + activity + trend
      decisions.py                    # Officer AGREE/DISAGREE
      scoring.py                      # Stage 2 batch trigger
      audit.py                        # Audit log
      active_learning.py              # AL queue + labeling
      ingest.py                       # File upload
    core/
      config.py                       # Settings (paths, thresholds)
    db/
      database.py                     # Async SQLAlchemy engine
      models.py                       # 6-table ORM schema
    pipeline/
      feature_extractor.py            # 5 feature families, 100+ regex
      stage1_filter.py                # TF-IDF + LogReg + lexicon override
      stage2_classifier.py            # DistilBERT + XGBoost + OOD + IOGP + SHAP + IG
      stage2_runner.py                # Batch scoring orchestrator
      ingestion_service.py            # File parsing + metadata + text-only mode
  venv/                               # Python virtual environment
  requirements.txt
```

### Frontend (`frontend/`)

```
frontend/
  src/
    App.tsx                           # Router + sidebar nav
    api.ts                            # Typed fetch wrapper for all endpoints
    index.css                         # Design system (dark mode, variables)
    main.tsx                          # Entry point
    views/
      TriageDashboard.tsx             # Officer queue (filters + stat cards + table)
      ReportDetail.tsx                # Officer card (gauge + highlights + SHAP + sign-off)
      ManualReviewQueue.tsx           # OOD / low-confidence queue
      LeadershipDashboard.tsx         # 5-panel analytics (site, IOGP, cause, activity, trend)
      ActiveLearning.tsx              # Uncertainty sampling queue
      IngestView.tsx                  # File upload
      AuditLog.tsx                    # Decision audit trail
  package.json
  vite.config.ts
  tsconfig.json
```

### ML (`ml/`)

```
ml/
  models/
    stage2_xgb.pkl                    # Trained XGBoost + Platt calibration
    stage2_scaler.pkl                 # StandardScaler (783-dim)
    stage2_ood.pkl                    # Mahalanobis OOD detector
    stage2_metrics.json               # Evaluation metrics
  scripts/
    train_stage2.py                   # Full training pipeline
  notebooks/                          # EDA / prototyping
```

### Data (`data/`)

```
data/
  synthetic/
    generate_dataset.py               # 1,100-line generator with Oil India framing
    batch_01.jsonl through batch_06.jsonl
    synthetic_oilgas_3000.jsonl       # Compiled 3,000-record dataset (2.26 MB)
  raw/                                # Original CSV datasets
  labeled/                            # Labeled subsets
  seed/                               # Initial seed data
```

### Root Files

| File | Purpose |
|---|---|
| `start.bat` | One-click launcher for both backend and frontend |
| `sih165.db` | SQLite database (850 reports, predictions, features) |
| `SIH165_Consolidated_Project_Information_Finalv1.md` | Domain theory reference (35 KB) |
| `Final System Architecture 165.md` | ASCII architecture diagram |
| `sih165-frontend-layout-structure.md` | UI blueprint / information architecture |

---

## 10. How to Run

### Prerequisites

- Python 3.12 with `venv` in `backend/venv/`
- Node.js 18+ with npm
- All Python deps installed (`pip install -r requirements.txt` in backend venv)
- All Node deps installed (`npm install` in frontend/)

### Quick Start

```bat
REM From project root:
start.bat
```

Or manually:

```powershell
# Terminal 1 — Backend
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

### URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

---

## 11. Known Limitations & Future Work

### Current Limitations

| # | Limitation | Impact | Mitigation |
|---|---|---|---|
| 1 | **Synthetic data** — model trained on generated reports, not real OIL data | Perfect metrics do not reflect real-world performance | OOD detector routes unfamiliar reports to NEEDS_REVIEW |
| 2 | **English-only NLP** — DistilBERT and all regex are English | Hindi/Assamese reports get garbage embeddings | OOD detector catches them and routes to manual queue (safe failure mode) |
| 3 | **SQLite** — single-file DB, no concurrency for production loads | Fine for prototype, not for 1000+ concurrent users | Swap to PostgreSQL for production |
| 4 | **No real TreeSHAP** — `shap` package may not be installed | Falls back to heuristic attribution (visually identical) | `pip install shap` |
| 5 | **No real Integrated Gradients** — IG spans use regex matching, not token-level gradients | Correct phrases highlighted but not gradient-computed | Implement `captum` IG for true token attribution |
| 6 | **No authentication** — no login, no role-based access control | Anyone can access any view | Add JWT auth + role middleware for production |

### Opted-for Future Fix

| Fix | Description | Status |
|---|---|---|
| **MuRIL swap** | Replace `distilbert-base-uncased` with `google/muril-base-cased` for Hindi + Assamese support | **Opted — not yet implemented** |

### Additional Future Work

| Enhancement | Description |
|---|---|
| **Hindi/Assamese lexicon** | Add Devanagari and Assamese script terms to Stage 1 lexicon override |
| **Translation pre-processing** | Add `langdetect` + IndicTrans2 for on-the-fly translation before pipeline |
| **Real-time ingestion** | Replace file upload with streaming API that accepts HSSE platform webhooks |
| **PostgreSQL migration** | Swap SQLite for PostgreSQL with proper connection pooling |
| **JWT authentication** | Add role-based access (Officer sees Triage, Leadership sees Dashboard only) |
| **PDF/image OCR** | Add Tesseract OCR for scanned handwritten reports |
| **Email/SMS alerts** | Notify officers when high-confidence SIF reports are ingested |
| **Model retraining cron** | Periodic retraining as active learning labels accumulate |

---

> **Last updated:** 2026-09-30
> **Authors:** Built during SIH165 prototype development session
