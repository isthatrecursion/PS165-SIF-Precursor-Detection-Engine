        SAFETY REPORTS
    (CSV / Excel + Free Text)
               │
               ▼
        FastAPI Backend
          Text Processing
               │
        ┌──────┴──────┐
        │             │
    [OCR low?]   [Processable]
        │             │
        ▼             │
   Manual Review      │
   Queue              │
   "Cannot process"   │
                      ▼
     ┌────────────────────────────┐
     │   DOMAIN FEATURE           │
     │   EXTRACTION               │
     │                            │
     │  Energy-Source Keywords    │
     │  electrical · fall/gravity │
     │  pressure · mechanical ·   │
     │  thermal · LOTO · SIMOPS   │
     │  H2S · BOP · confined      │
     │                            │
     │  Barrier-Failure Phrases   │
     │  "not isolated"            │
     │  "no permit obtained"      │
     │  "PPE not worn"            │
     │  "bypassed" · "no gas test"│
     │                            │
     │  [Structured metadata      │
     │   missing (site/equip.)?   │
     │   → degrade to text-only   │
     │   mode, lower-confidence   │
     │   flag carried forward —   │
     │   pipeline continues]      │
     └────────────┬───────────────┘
                  │
                  ▼
     ┌────────────────────────────┐
     │  STAGE 1                   │
     │  High-Recall Filter        │
     │                            │
     │  TF-IDF +                  │
     │  Logistic Regression       │
     │  + Lexicon rules           │
     │                            │
     │  Target: near-100% recall  │
     │  (deliberately over-flags) │
     │  Runs inline · synchronous │
     │  Flags ~30–40% of volume   │
     └──────────┬─────────────────┘
                │
      ┌─────────┴──────────┐
      ▼                    ▼
  FLAGGED              CLEARED
  (~30–40%)            (~60–70%)
  → Stage 2            → Routine queue
                         No transformer
                         inference
      │
      ▼
     ┌────────────────────────────────────────┐
     │  STAGE 2                               │
     │  Precise Classifier                    │
     │  (batch · within one shift window)     │
     │                                        │
     │  ┌──────────────┐  ┌────────────────┐  │
     │  │ DistilBERT / │  │ Domain         │  │
     │  │ RoBERTa-base │  │ Features       │  │
     │  │ fine-tuned   │  │                │  │
     │  │              │  │ energy-type    │  │
     │  │ Text         │  │ flags          │  │
     │  │ Embedding    │  │ barrier-fail   │  │
     │  │              │  │ phrase flags   │  │
     │  │              │  │ site / equip.  │  │
     │  │              │  │ shift metadata │  │
     │  └──────┬───────┘  └───────┬────────┘  │
     │         └────────┬─────────┘           │
     │                  ▼                     │
     │          XGBoost Decision Layer        │
     │                  ▼                     │
     │          Platt Scaling                 │
     │          Calibration                   │
     │                  ▼                     │
     │          OOD Detection                 │
     │          (Mahalanobis distance         │
     │           vs. training space)          │
     │                  ▼                     │
     │   Deployed recall floor: ≥90% overall  │
     │   (policy threshold, not a Stage-1 or  │
     │    Stage-2-specific number)            │
     └──────────────────┬─────────────────────┘
                        │
           ┌────────────┴────────────┐
           ▼                         ▼
        HIGH                LOW-CONFIDENCE /
     CONFIDENCE              AMBIGUOUS / OOD
        │                         │
        │                         ▼
        │                  Mandatory
        │                  Manual Review
        │                  "Low-confidence,
        │                   ambiguous, or
        │                   novel — needs
        │                   officer"
        ▼
         OUTPUTS
         ─────────────────────────────────
         • SIF Flag (binary)
         • Calibrated probability (%)
         • IOGP Life-Saving Rule tags
           (multi-label):
           Energy Isolation
           Hot Work
           Confined Space
           Line of Fire
           Working at Height
           SIMOPS
           Driving
           Bypassing Safety Controls
           Safe Mechanical Lifting
               │
               ▼
     ┌─────────────────────────────┐
     │  EXPLAINABILITY             │
     │                             │
     │  TreeSHAP                   │
     │  → XGBoost / structured     │
     │    feature layer            │
     │  → Feature importances      │
     │    (e.g. barrier_fail=LOTO, │
     │     energy=electrical)      │
     │                             │
     │  Integrated Gradients       │
     │  → DistilBERT text layer    │
     │  → Highlighted phrase(s)    │
     │    in original report text  │
     │                             │
     │  [Attention weights:        │
     │   supplementary only —      │
     │   not primary explanation]  │
     └──────────────┬──────────────┘
                    │
          ┌─────────┴──────────┐
          ▼                    ▼

  OFFICER-FACING CARD     LEADERSHIP DASHBOARD
  (per-report triage)     (pattern view)

  Risk Score: 82%         Site × Activity × Rule
  (calibrated)            density / trend view

  IOGP Rule:              Precursor frequency
  Energy Isolation        by site, equipment
                          type, rule category
  Highlighted phrase:
  "isolation not          Emerging clusters
   confirmed before       visible across
   re-energizing line"    rolling time window

  Flags:
  barrier_fail = LOTO
  energy = electrical

  Confidence: HIGH
  → Priority review

          │                    │
          └─────────┬──────────┘
                    ▼
          HUMAN VALIDATION
          ─────────────────────
          Safety Officer:
          [ Agree — SIF Precursor   ]
          [ Disagree — Not serious  ]
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
    FINAL DECISION        OVERRIDE LOG
    (officer-owned,       every decision
     auditable)           recorded:
                          report + score
                          + officer action
                               │
                  ┌────────────┼──────────────┐
                  ▼            ▼              ▼
           ACTIVE          PLATT          PER-SITE
           LEARNING        RECALIB-       RECALL
           QUEUE           RATION         AUDIT
           Lowest-conf.    Quarterly      Site-based
           predictions →   ECE check +   holdout
           officer label   reliability   checks for
           queue           diagram       underperform-
                           re-run        ing sites