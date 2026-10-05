# SIH165 — Frontend Layout Structure
### SIF Precursor Detection Engine — UI Blueprint

This structure is derived directly from the corrected system architecture and the solution-approach document. It's stack-agnostic (works for React, Vue, or plain HTML/CSS) — treat it as an information-architecture + component blueprint, not a specific framework's code.

---

## 1. Application Map (Top-Level Views)

| # | View | Primary User | Purpose |
|---|------|--------------|---------|
| 1 | **Officer Triage Dashboard** | HSE Safety Officer | Queue-sorting — "which report do I read first?" |
| 2 | **Report Detail (Officer Card)** | HSE Safety Officer | Per-report decision — the auditable card from Section 6.3 |
| 3 | **Manual Review Queue** | HSE Safety Officer | Reports that bypassed automated scoring (OCR fail / low-confidence / ambiguous-OOD / missing metadata) |
| 4 | **Leadership Dashboard** | Site/Regional HSE Leadership | Pattern view — "where do I send inspection resources?" |
| 5 | **Active Learning Queue** | ML/Admin team | Lowest-confidence predictions routed for labeling |
| 6 | **Override / Audit Log** | ML/Admin team, Leadership | Accountability trail of every officer decision |

Role-based navigation:
- **Safety Officer** → Triage Dashboard, Manual Review Queue, Report Detail
- **Leadership** → Leadership Dashboard only (no per-report access — matches Section 8.4's no-reporter-scoring commitment)
- **Admin/ML team** → Active Learning Queue, Audit Log

---

## 2. View-by-View Breakdown

### 2.1 Officer Triage Dashboard
**Layout:** Header + left filter rail + main queue table

- **Header bar:** app title, officer identity, current shift-window indicator, unread-flag count badge
- **Filter rail (left sidebar):**
  - Site selector
  - Confidence band (High / needs review)
  - IOGP Rule category
  - Date range
  - Status (Unreviewed / Reviewed)
- **Main content — Report Queue Table**, sorted by risk score descending by default (matches the queue-sorting use case, Section 1B):
  | Report ID | Site | Submitted | Risk Score | IOGP Rule(s) | Confidence | Status |
  - Row click → opens Report Detail

---

### 2.2 Report Detail / Officer-Facing Card
This is the core UI artifact (Section 6.3) — build this first since it's the "auditability" proof-point for judges.

**Layout:** Two-column — text panel (left/main) + score panel (right/sidebar)

- **Top strip:** Report ID, site, date, reporter *role* only (no identity — Section 8.4)
- **Score panel (right):**
  - Calibrated risk score (e.g. "82%") — large numeral
  - Confidence band badge (High / Low / Ambiguous / OOD)
  - Matched IOGP Life-Saving Rule chips (multi-label)
  - Matched structured flags list (e.g. `barrier_fail = LOTO_not_verified`, `energy_type = electrical`)
- **Text panel (left/main):**
  - Full report text with **highlighted phrase spans** (integrated-gradients output) — hover/tap shows "this phrase drove the score"
- **Explainability drawer (collapsible):**
  - TreeSHAP feature-importance bar chart (structured layer)
  - Note distinguishing text-layer attribution (integrated gradients) from structured-layer attribution (TreeSHAP) — don't merge into one generic "explanation" widget
- **Low-confidence / Ambiguous / OOD state:** score panel is replaced by a banner: *"Low confidence / novel report — needs officer review"* rather than showing a number that looks confident
- **Action bar (bottom, sticky):**
  - `[ Agree — SIF Precursor ]`
  - `[ Disagree — Not serious ]`
  - (No "Escalate" button — not specified in the source document; add only if you decide to extend scope)

---

### 2.3 Manual Review Queue
Catches everything routed away from normal scoring: OCR failures, low-confidence, ambiguous/OOD, missing-metadata (text-only mode) reports.

**Layout:** Single table, same shape as Triage Dashboard but with a **Reason** column

| Report ID | Reason for Routing | Site | Date | Status |
|---|---|---|---|---|
| — | OCR failed / Low-confidence / Ambiguous-OOD / Missing metadata | — | — | — |

- Row click → same Report Detail card component, with the banner state active instead of a score

---

### 2.4 Leadership Dashboard
**No individual reports shown here** — aggregation only, per Section 1B and the no-reporter-scoring commitment (8.4).

**Layout:** Header filters + grid of visualization panels

- **Top filter bar:** rolling time window, site, activity type
- **Panel 1 — Site × Activity × Rule density matrix/heatmap**
- **Panel 2 — Precursor frequency trend** (line/area chart, per IOGP rule category, over the rolling window)
- **Panel 3 — Emerging clusters callout** (ranked list: sites/activities with rising precursor density)
- **Panel 4 — Per-site recall/coverage audit** (Section 8.2 data-equity check) — visually flags sites where held-out recall falls below the overall average, so leadership can see where the model is least trustworthy, not just where risk is highest

---

### 2.5 Active Learning Queue (internal/admin)
**Layout:** List + inline labeling panel

- List of lowest-confidence predictions awaiting officer correction
- Each item expands to: report text, model's current guess, correction controls (confirm / relabel SIF flag, assign/adjust IOGP rule tags)

---

### 2.6 Override / Audit Log
**Layout:** Simple filterable table

| Report ID | Model Score | Officer Action | Officer Role | Timestamp |
|---|---|---|---|---|

Doubles as the accountability trail and the active-learning feed (Section 8.3).

---

## 3. Shared / Reusable Components

| Component | Used in | Notes |
|---|---|---|
| `ConfidenceBadge` | Triage table, Report Detail | Color-coded: High / Low / Ambiguous-OOD |
| `IOGPRuleChip` | Triage table, Report Detail, Dashboard | Multi-label capable |
| `HighlightedTextViewer` | Report Detail | Renders integrated-gradients spans with tooltips |
| `ScoreGauge` | Report Detail | Calibrated probability display |
| `FeatureImportanceChart` | Report Detail (explainability drawer) | TreeSHAP bar chart |
| `SiteFilterSelector` | Dashboard, Triage, Manual Queue | Shared filter control |
| `DateRangePicker` | Dashboard, Triage | Shared filter control |
| `StatusPill` | Triage table, Manual Queue | Unreviewed / Reviewed |
| `ReasonTag` | Manual Review Queue only | OCR-fail / Low-confidence / Ambiguous-OOD / Missing-metadata |

---

## 4. Suggested Build Order

1. `ConfidenceBadge`, `IOGPRuleChip`, `StatusPill` (small shared atoms)
2. Report Detail / Officer Card (the highest-value screen for demo purposes — matches what Section 10.1 names as MVP)
3. Officer Triage Dashboard (table + filters)
4. Manual Review Queue (reuses Report Detail + adds `ReasonTag`)
5. Leadership Dashboard (needs aggregation data, so naturally comes after per-report scoring works)
6. Active Learning Queue + Audit Log (admin-only, lowest priority for a judge-facing demo)

This order matches the document's own build sequence in Section 10.3 — proxy data and scoring first, dashboard/officer-card UI last, built against real model outputs rather than placeholder numbers.
