# SIH165 — Consolidated Domain & Solution Intelligence

## Purpose



The purpose is to provide one working reference for designing the **AI/NLP Engine to Detect Serious Injury & Fatality (SIF) Precursors in OIL Unsafe-Act, Unsafe-Condition and Near-Miss Reports**.

> **Important source note:** a 'Source' taken into consideration is a Nayara Energy educational presentation. Its first page explicitly states that it does not represent or constitute the position of OISD unless expressly stated otherwise. It is therefore useful as an industry-practice reference, not as an OIL-specific policy source.

---

# 1. Core Problem Formulation

## 1.1 What the system should detect

The solution framework recommends two core prediction tasks:

### A. Binary SIF-precursor classification

Determine whether an already-submitted report describes a condition with **SIF potential**.

The working conceptual definition in the solution framework is:

> **High-energy exposure + failed or absent safety barrier**

The framework explicitly distinguishes this from simply classifying how severe the report sounds.

Example:

- A report about a minor slip with alarming language may have low SIF potential if there was no meaningful high-energy exposure.
- A mundane report stating that a valve was not isolated before maintenance may have high SIF potential because energy was present and the required barrier was missing.

### B. Multi-label Life-Saving Rule tagging

Identify which Life-Saving Rule categories apply to a report.

A single report can map to more than one rule.

### C. Precursor pattern aggregation

Instead of making phrase extraction the main per-report prediction task, the framework recommends using the classifier output to aggregate recurring patterns by:

- site
- activity
- equipment
- Life-Saving Rule
- precursor/category

This supports a leadership dashboard.

---

# 2. Key Domain Concept: Energy + Barrier

The solution framework grounds SIF detection in a two-part structure:

## Energy source

Examples include:

- Electrical
- Stored energy
- Mechanical motion
- Gravity / fall
- Pressure
- Chemical
- Thermal / ignition
- Kinetic / vehicle motion
- Combined concurrent energy sources

## Barrier

A barrier is the control that should prevent exposure to the hazardous energy.

Examples:

- LOTO / verified isolation
- Work permit
- Gas testing
- Fire watch
- Ventilation
- Entry authorization
- Guardrails
- Fall-arrest system
- Exclusion zone / barricading
- Journey-management controls
- Safety interlock
- Authorization before bypassing safety systems
- Lift plan / certified lifting equipment

## Core NLP pattern

The useful conceptual pattern is:

```text
HIGH / RELEVANT ENERGY
        +
BARRIER ABSENT / FAILED / BYPASSED / NOT VERIFIED
        ↓
SIF-PRECURSOR SIGNAL
```

This should be preferred over keyword counting or sentiment classification.

---

# 3. OIL / OISD Definitions Relevant to Dataset Labels

## 3.1 Near Miss

`OIL SIH 3.pdf` defines a near miss as an incident that does not result in injury or property damage but has the potential to result in injury and/or property damage. It is an undesirable event which, if not timely controlled, could have led to a major or minor incident.

## 3.2 Hi-Po Near Miss

A **High Potential (Hi-Po) Near Miss** is defined as a near miss that, under other circumstances, could realistically have resulted in one or more fatalities.

This is highly relevant for SIF-precursor labeling and is a strong candidate for:

- a positive-label source
- a weak-supervision rule
- a validation/reference label

It should not automatically be assumed to be perfectly identical to the final SIF label without domain validation.

## 3.3 Unsafe Act

An Unsafe Act is an act that deviates from a generally recognized safe method or specified job method and increases the probability of an incident.

## 3.4 Unsafe Condition

An Unsafe Condition is a condition or situation — including electrical, chemical, biological, physical, mechanical and/or environmental conditions — that increases incident risk.

These definitions support an explicit dataset field:

```text
report_type =
    Unsafe Act
    Unsafe Condition
    Near Miss
```

---

# 4. Recommended Dataset Schema

The combined material supports a richer dataset than a simple:

`report_text -> SIF yes/no`

A practical schema is:

| Field | Purpose |
|---|---|
| `report_text` | Original report narrative |
| `report_type` | Unsafe Act / Unsafe Condition / Near Miss |
| `hazard_type` | Electrical / Chemical / Physical / Mechanical / Environmental / etc. |
| `energy_type` | Energy source detected |
| `barrier_required` | Control expected to prevent exposure |
| `barrier_status` | Present / Missing / Failed / Bypassed / Not Verified / Unknown |
| `life_saving_rule` | One or more relevant LSRs |
| `cause_category` | Standardized incident cause(s) |
| `hi_po` | Whether report qualifies as Hi-Po Near Miss where applicable |
| `sif_precursor` | Main binary target |
| `site` | Site / installation |
| `activity` | Work/activity being performed |
| `equipment` | Relevant equipment/asset |
| `corrective_action` | Action taken/recommended |
| `investigation_findings` | Findings where available |
| `investigation_status` | Whether / how the event progressed through investigation |
| `learning_provenance` | OISD Case Study / Internal Safety Alert / None or Not Applicable |
| `outcome` | Actual incident outcome, if any |
| `date/time` | Temporal analysis |
| `confidence` | Model confidence |
| `review_status` | Human-confirmed / overridden / pending |

The exact fields available in OIL's actual reporting platform remain an open dependency.

---

# 5. Standardized Incident Cause Categories

`OIL SIH 3.pdf`, page 25, presents a standardized cause list that can become an important **cause taxonomy** for the NLP engine.

Important categories:

1. Violation of Work Permit System
2. Inadequate Hazard Identification / Risk Assessment
3. Inadequate Work Standards / Procedures / Disregard of SOP
4. Inadequate Competence
5. Inadequate Supervision
6. Design Deficiency
7. Non-compliance with Management of Change
8. Poor Maintenance & Inspection
9. Negligent Driving / Road / Crane / Hydra accidents
10. Inadequate / defective warning systems or safety devices
11. Non-compliance with PPE / fall & slip
12. Equipment Failure
13. Other

**Note:** `Pilferage / miscreant activities` should be treated as a **cause/contributing-factor category**, not as an automatic SIF signal. The source establishes it as an incident cause category; it does not state that pilferage by itself implies SIF potential.

This enables a richer task formulation:

```text
Report
  ↓
SIF precursor?
  +
Life-Saving Rule(s)
  +
Cause / contributing factor(s)
```

A report could therefore be tagged with multiple cause categories where justified.

---

# 6. HIRA as a Safety Reasoning Framework

The OISD SMS document defines HIRA (Hazard Identification and Risk Analysis) as a process intended to:

- identify hazards
- evaluate risk
- reduce likelihood and/or consequences
- recommend preventive and mitigation measures

The document distinguishes:

- **Hazard Identification** — identifying hazards before they can be assessed and controlled
- **Risk Analysis** — evaluating frequency and severity qualitatively, semi-quantitatively or quantitatively

The HIRA scope also includes:

- process hazards
- previous incidents with catastrophic potential
- engineering and administrative hazard controls
- interrelationships between controls
- consequences of control failure
- human factors affecting safety barriers/controls
- evaluation of the effect of control failure on workforce safety and health

### NLP implication

The model should conceptually extract:

```text
HAZARD
  ↓
ENERGY / EXPOSURE
  ↓
CONTROL / BARRIER
  ↓
CONTROL STATUS
  ↓
POTENTIAL CONSEQUENCE
```

This makes the classifier more domain-aware.

---

# 7. Process Safety Information (PSI)

The OISD SMS material defines Process Safety Information as written information covering technologies, operations and equipment used in a facility.

Relevant categories include:

- Process and chemical information
- Process technology
- Process equipment
- Process descriptions
- Process chemistry
- Process Flow Diagrams / PFDs
- P&IDs
- Material and energy balances
- Safe upper/lower operating limits
- Safety-critical equipment
- Interlocks and control-system logic
- HIRA reports

The document says PSI supports other safety-management elements such as:

- HIRA
- training
- operating procedures
- mechanical integrity
- management of change
- emergency response
- incident investigation

### Project implication

PSI is a potential future structured-data source.

A future architecture could combine:

```text
Incident Report
+
Site / Equipment Metadata
+
HIRA / PSI Context
+
SOP / Permit Context
      ↓
SIF Intelligence Engine
```

This should be considered a future integration unless the actual OIL systems provide the data.

---

# 8. Operating Procedures, SOP and Safe Work Practices

The OISD SMS material emphasizes that operating procedures should be:

- clear
- concise
- accurate
- unambiguous
- specific to the operation/installation
- available to personnel
- used for safe operation, troubleshooting, emergency handling and training

SOP content should address:

- responsibility
- HSE considerations
- tools and tackles
- PPE
- hazards
- preventive measures
- consequences
- corrective steps

The material also references:

- work permits
- JSA / JHA
- Toolbox Talks
- safe work practices
- authorization
- management of change
- incident learnings

### NLP implication

These concepts can provide a strong domain lexicon.

Example feature families:

```python
energy_terms
barrier_terms
permit_terms
PPE_terms
isolation_terms
gas_test_terms
JSA_terms
TBT_terms
authorization_terms
interlock_terms
SOP_terms
```

---

# 9. Life-Saving Rule Taxonomy

The solution framework maps Life-Saving Rules to energy and barriers.

The working rule set includes:

| Life-Saving Rule | Energy / exposure | Expected barrier |
|---|---|---|
| Energy Isolation | Stored / electrical / mechanical | LOTO and verified isolation |
| Hot Work | Thermal / ignition | Gas test, permit, fire watch |
| Confined Space | Asphyxiation / toxic atmosphere | Gas test, ventilation, authorization |
| Line of Fire | Kinetic / gravity / pressure | Exclusion zones, barricading |
| Working at Height | Gravity / fall | Fall-arrest system, lifeline, guardrails, permit |
| SIMOPS | Multiple concurrent energies | SIMOPS assessment, coordination, zoning |
| Driving | Vehicle kinetic energy | Seatbelt, speed control, journey management |
| Bypassing Safety Controls | Energy protected by bypassed control | Authorization and safety-critical-device protection |
| Safe Mechanical Lifting | Gravity / mechanical / suspended load | Lift plan, certified equipment, exclusion zone |

`OIL SIH 2.pdf` independently presents a 10-rule Life-Saving Rule set including:

- valid work permit
- gas testing
- confined-space authorization
- isolation verification
- authorization before overriding/disabling safety systems
- fall protection
- driving controls
- no smoking
- no drugs/alcohol on site
- no walking under suspended loads

Because that document is a Nayara Energy presentation, treat it as industry-practice reference rather than direct OIL policy.

---

# 10. Interlock Bypass as a High-Value NLP Signal

The OISD SMS material describes interlock bypass management and emphasizes that bypassing an interlock can expose operations to unknown hazards.

It calls for:

- keeping interlocks in line wherever possible
- documented bypass procedures
- approval authority
- a bypass register
- reason for bypass
- compensatory measures
- precautions
- restoring the bypassed interlock
- review of continued necessity

The project-relevant NLP feature is:

```text
safety_control_bypass =
    interlock bypassed
    safety interlock overridden
    alarm disabled
    ESD bypassed
    trip bypassed
    safety system overridden
```

This is a particularly useful barrier-failure feature.

---

# 11. Safety-Critical Equipment and Controls

The OISD SMS material references safety-critical equipment and systems such as:

- PSV
- TSV
- gas detectors
- H2S detectors
- fire alarms
- smoke/heat detectors
- firefighting facilities
- safety interlocks
- DCS / alarms
- isolation valves
- blinds
- drains / vents
- control valves / SDVs

These can become part of the equipment/control vocabulary for the NLP engine.

A useful conceptual distinction is:

```text
Safety-critical equipment mentioned
        +
Failure / overdue / bypass / unavailable
        ↓
Potential precursor signal
```

---

# 12. Incident Reporting and Investigation Workflow

The OIL/OISD reporting material describes a structured workflow around:

```text
Incident
   ↓
FIR
   ↓
Investigation
   ↓
IIR
   ↓
Review
   ↓
Learning / Safety Alert / Case Study
```

The material says incident investigations should be initiated promptly, while securing the incident scene, evidence, information and people/environment.

Investigation reporting may contain:

- physical observations
- process parameters
- timestamps
- key witnesses
- photographs
- key factors
- analysis
- recommendations

### Project implication

Initial reports and subsequent investigation reports can form a learning pipeline:

```text
Initial Report
      +
Investigation Report
      +
Cause
      +
Corrective Action
      +
Final HSE Review
      ↓
Verified training example
```

This could eventually reduce dependence on cold manual labeling.

---

# 13. Reporting and Incident Data

The OISD reporting material indicates that quarterly reporting can include:

- number of Unsafe Acts
- number of Unsafe Conditions
- number of Near Misses
- injuries
- minor incidents
- major incidents
- lost man-days
- million-man-hours worked
- HSE-related incidents
- details of minor incidents / Hi-Po Near Misses where required

This provides a useful dashboard structure.

Example:

```text
Safety Intelligence Dashboard

Reports analysed
Unsafe Acts
Unsafe Conditions
Near Misses
Hi-Po Near Misses
SIF Precursors

Breakdown:
  Site
  Activity
  Equipment
  Life-Saving Rule
  Cause
  Time period
```

---

# 14. Investigation / Learning Provenance

`OIL SIH 3.pdf` makes an explicit distinction between two downstream learning artifacts:

- **Case Study:** detailed lessons learned from an incident investigation report for an incident investigated by OISD.
- **Safety Alert:** lessons learned from an incident that was not investigated by OISD, based on the company's internal investigation report.

This is useful metadata because it records the **provenance and investigation pathway** of an event.

Recommended fields:

```text
investigation_status
learning_provenance
```

Possible values for `learning_provenance`:

```text
OISD Case Study
Internal Safety Alert
None / Not Applicable
```

### Important modeling constraint

These fields should **not be used as initial prediction inputs** when the model is evaluating a report at submission time.

The causal sequence is:

```text
Initial Report
      ↓
AI / HSE Triage
      ↓
Investigation / Review
      ↓
Case Study or Safety Alert
```

Therefore, using `Case Study / Safety Alert` as an input to the initial SIF prediction could introduce **future-information leakage**.

They are better used as:

- post-event metadata
- retrospective analysis
- investigation/provenance tracking
- downstream validation context
- dashboard analytics
- future research tasks where post-investigation information is intentionally available

The source establishes a distinction in **investigation/provenance**, not a formal severity ranking. It should therefore not be treated as a direct severity score.

---

# 15. Incident Classification Information

The `OIL SIH 3.pdf` material describes several major-incident criteria, including events involving:

- fire not extinguished within the stated threshold
- explosion / blowout / radioactive leakage or loss
- prolonged operational shutdown
- major financial loss
- fatality within the installation
- permanent loss of body part / permanent disability
- major loss of containment with external impact
- high cumulative lost time
- qualifying road-transport incidents

The exact thresholds shown in the source should be retained only when they are required for the particular OISD reporting/classification use case.

For the SIF-precursor project, these **actual outcome/classification criteria should not replace precursor detection**, because the solution framework intentionally separates potential severity from realized outcome.

---

# 16. Leading and Lagging Safety Indicators

`OIL SIH 2.pdf` describes a process-safety indicator hierarchy:

- **Tier 1:** Major consequence Loss of Primary Containment (LOPC)
- **Tier 2:** Minor consequence LOPC
- **Tier 3:** Challenge to safety system
- **Tier 4:** Operational discipline and management-system performance

Examples shown include:

- interlock bypass
- overdue PSV calibration
- process near miss
- emergency drills
- ITPM %
- compliance with RCA / HAZOP / QRA / SIL recommendations

The presentation also references leading and lagging indicator approaches.

### Project implication

Our system operates in the **precursor / leading-indicator space** rather than waiting for Tier-1-type outcomes.

The dashboard can therefore combine:

```text
Precursor reports
+
Barrier failures
+
Near misses
+
Cause categories
+
Trend
```

---

# 17. Site Safety Observation as a Possible Future Input

`OIL SIH 2.pdf` describes a Site Safety Observation (SSO) system in which employees and leadership observe at-risk/safe behaviour and unsafe acts/conditions and corrective actions are expected.

This suggests a future extension:

```text
Unsafe Act
Unsafe Condition
Near Miss
Site Safety Observation
       ↓
Common NLP Engine
```

For the current SIH MVP, this should remain future scope unless the problem specification confirms the data source.

---

# 18. Safety Reporting Culture

The source materials emphasize encouraging:

- reporting of unsafe acts
- reporting of unsafe conditions
- near-miss reporting
- workforce participation
- sharing of lessons

The project framework identifies an important design requirement:

**The AI should analyze the event and hazard, not score the individual reporter.**

Reporter identity should therefore not be used as a risk feature or leaderboard variable.

The system should support:

```text
Report
  ↓
AI analysis
  ↓
Human review
```

rather than:

```text
Employee
  ↓
AI score of employee
```

This is important for preserving reporting participation.

---

# 19. Incident Learning and Historical Pattern Detection

The OISD SMS material states that incident information should be maintained in an incident database in a form suitable for use and that investigation reports should be retained for at least five years to help determine whether incident patterns develop or exist.

This strongly supports a longitudinal project component:

```text
Historical reports
       ↓
SIF classification
       ↓
Energy / Barrier / Cause extraction
       ↓
Aggregation over time
       ↓
Recurring precursor patterns
```

Possible dimensions:

- site × rule
- activity × rule
- equipment × barrier failure
- cause × site
- precursor × time period

---

# 20. Recommended NLP Feature Families

Based on the combined materials, the strongest domain-engineered feature families are:

## A. Energy features

```text
electrical
pressure
stored energy
mechanical
gravity
fall
thermal
chemical
kinetic
vehicle
suspended load
```

## B. Barrier-status features

```text
not isolated
isolation not verified
LOTO not performed
no permit
permit not obtained
gas test not performed
PPE not worn
guardrail missing
harness not used
barricade missing
interlock bypassed
alarm disabled
authorization not obtained
```

## C. Hazard categories

```text
electrical
chemical
biological
physical
mechanical
environmental
```

## D. Safety-management features

```text
HIRA
JSA
JHA
SOP
TBT
work permit
MOC
PSSR
PSI
safety critical equipment
```

## E. Equipment/control features

```text
PSV
TSV
DCS
ESD
SDV
gas detector
H2S detector
fire alarm
isolation valve
blind
drain
vent
pump
compressor
pipeline
tank
reactor
```

---

# 21. Proposed Model Output

A useful officer-facing output should contain more than a probability.

Example:

```text
SIF PRECURSOR
HIGH

Reason:
High-energy exposure + barrier failure

Energy:
Electrical / stored energy

Barrier:
Isolation not verified

Life-Saving Rule:
Energy Isolation

Cause:
Violation / deficiency in work control
(only where supported by verified labels)

Hi-Po Near Miss:
Yes / No / Not Applicable

Evidence:
"...isolation was not verified before maintenance..."

Confidence:
High / Ambiguous / Novel

Action:
HSE Officer Review
```

The solution framework recommends showing highlighted phrases and structured explanation rather than presenting a black-box score alone.

---

# 22. Recommended Architecture

The solution framework proposes a **two-stage cascade**.

## Stage 1 — high-recall filter

Inputs:

- rule-based energy/barrier lexicon
- TF-IDF
- Logistic Regression

Purpose:

- process every report cheaply
- prioritize recall
- avoid allowing likely precursors to disappear before deeper review

## Stage 2 — precise classifier

Inputs:

- transformer text representation
- energy features
- barrier-status features
- Life-Saving Rule features
- structured metadata such as site/equipment/shift where available

Proposed model:

```text
DistilBERT / RoBERTa
        ↓
Text embedding
        +
Domain features
        +
Structured metadata
        ↓
XGBoost decision layer
```

Outputs:

- calibrated SIF-precursor probability
- multi-label Life-Saving Rule tags
- explanation / highlighted evidence

---

# 23. Baselines and Rejected Approaches

The framework explicitly recommends building a naive rule-based baseline first.

Example:

```text
ENERGY TERM
    +
BARRIER-FAILURE TERM
    ↓
FLAG
```

It is:

- fast
- explainable
- zero-label
- useful as a fallback

Other approaches considered in the framework include:

### TF-IDF / classical ML

Useful as a baseline and for structured-feature integration, but weaker for contextual meaning and negation.

### Fine-tuned BERT-family model

Useful for context, negation and phrasing variation.

### Transformer + XGBoost hybrid

Chosen as the main candidate because it combines contextual text understanding with structured/domain features.

### Large general-purpose LLM as production classifier

Not chosen as the core engine in the framework because of concerns around consistency, calibration, cost and domain-specific signal.

The framework retains LLMs as a possible **weak-label bootstrapping tool**, not as the production classifier.

### Graph Neural Network

Future scope because a mature site-equipment-incident graph is not yet available.

---

# 24. Evaluation Design

The project should not rely on accuracy alone.

The solution framework emphasizes:

- Recall on SIF-positive class
- Precision
- F2-score
- PR-AUC
- per-Life-Saving-Rule metrics

It proposes site-based and time-based validation.

## Why this matters

A random split may leak:

- site-specific wording
- incident-related wording
- reporting-cycle patterns

Therefore use:

### Time-based holdout

Train on earlier reports and test on later reports.

### Site-based holdout

Train on some sites and test on unseen sites.

Both should be reported.

---

# 25. Special Failure Cases to Test

The framework explicitly calls out:

1. Very short reports
2. Reports with ambiguous/absent energy language
3. Code-mixed Hindi-English or abbreviated text
4. Near-miss narratives
5. Unusual / novel scenarios
6. Poor OCR or garbled text

The intended behavior for insufficient information is not to confidently mark a report safe.

A three-way operational state is preferred:

```text
SIF Flagged
Non-SIF
Needs Human Review / Insufficient Detail
```

---

# 26. Explainability

The solution framework proposes different explanation methods for the different model components.

## Transformer text side

Use **Integrated Gradients** as the primary attribution method to highlight influential text spans.

## Tree / structured-feature side

Use **TreeSHAP** for the XGBoost/structured component.

The final UI should unify the explanations rather than expose two unrelated technical artifacts.

---

# 27. Calibration and Abstention

The solution framework recommends calibration because the probability shown to a safety officer should have interpretable meaning.

For an early small labeled dataset:

- Platt scaling is proposed as the starting calibration method.
- Isotonic regression can be reconsidered when more labeled data becomes available.

Metrics include:

- Expected Calibration Error (ECE)
- Brier score
- Reliability diagrams

For uncertain or novel reports:

```text
Mid-confidence
OR
Out-of-distribution
OR
insufficient information
        ↓
Mandatory human review
```

---

# 28. Responsible-AI / Safety Design

The framework highlights the asymmetric costs:

```text
False Negative:
Real precursor missed
→ potentially catastrophic consequence

False Positive:
Routine report reviewed
→ bounded officer time cost
```

Therefore:

- prioritize recall
- use carefully selected thresholds
- maintain human review
- avoid autonomous final safety decisions

The proposed system should be:

> **Decision-support, not decision-maker.**

Every officer override should ideally be logged so it can serve as:

- accountability information
- future training data
- active-learning signal

---

# 29. Graceful Degradation

Expected failure cases and behavior:

## Bad OCR / unreadable report

Do not force a model prediction.

Route to:

```text
Manual review
+ "Could not process / insufficient text"
```

## Missing structured metadata

Fall back to text-based pathway with lower confidence.

## Novel scenario

Use out-of-distribution / uncertainty handling and route to manual review.

General design principle:

> **Never fail silently into a falsely reassuring low-risk prediction.**

---

# 30. Deployment Concept

The solution framework recommends centralized inference rather than GPU-equipped field sites.

## Stage 1

Cheap enough to run at report submission.

## Stage 2

Centralized server/batch inference over Stage-1-flagged reports.

The project is a **triage/report-analysis system**, not a live emergency alarm, so sub-second inference is not the core requirement.

Integration should ideally be:

```text
Existing OIL HSSE / reporting platform
             ↓
       AI intelligence layer
             ↓
 Flags / tags / explanations
             ↓
Existing dashboard / HSE workflow
```

The project should not require the organization to re-enter the same report into a second independent system.

---

# 31. Dashboard Concept

Two user groups are identified.

## HSE Safety Officer

Needs:

- per-report priority
- SIF flag
- short reason
- Life-Saving Rule
- highlighted evidence
- confidence
- review action

## Site / Regional HSE Leadership

Needs:

- trends
- precursor density
- site comparisons
- activity patterns
- rule concentrations
- cause concentrations

Concept:

```text
                 REPORTS
                    ↓
             NLP CLASSIFIER
                    ↓
       ┌────────────┴────────────┐
       ↓                         ↓
Officer-level output       Leadership analytics
       ↓                         ↓
Flag + evidence            Site × activity × rule
LSR + cause                trends / density
```

---

# 32. Most Important Immediate Changes to the Project

Based on all supplied material, the following additions are especially valuable:

## Add to dataset

```text
report_type
hazard_type
energy_type
barrier_required
barrier_status
life_saving_rule
cause_category
hi_po
sif_precursor
site
activity
equipment
investigation_status
learning_provenance
```

## Add to NLP engine

```text
Energy detection
+
Barrier-failure detection
+
Cause classification
+
Life-Saving Rule tagging
+
Negation/context handling
```

## Add to dashboard

```text
SIF precursor count
Hi-Po Near Miss count
Barrier failure trends
Cause trends
Life-Saving Rule trends
Site/activity patterns
```

## Add to human-in-the-loop flow

```text
AI prediction
↓
Officer review
↓
Confirm / override
↓
Store feedback
↓
Future retraining
```

---

# 33. Overall Working System

The consolidated conceptual system is:

```text
                    SAFETY REPORT
                         │
             ┌───────────┼────────────┐
             ↓           ↓            ↓
        Report Type   Hazard/Energy  Narrative
             │           │            │
             └───────────┼────────────┘
                         ↓
                  Barrier Detection
                         │
              Present / Missing / Failed
                         │
                         ↓
               Domain Feature Layer
          ┌──────────────┼───────────────┐
          ↓              ↓               ↓
       Energy        Life-Saving       Cause
       Features        Rules          Categories
          │              │               │
          └──────────────┼───────────────┘
                         ↓
                Stage 1 High Recall
                 Lexicon + TF-IDF/LR
                         ↓
                Stage 2 Classifier
             DistilBERT / RoBERTa
                         +
              Structured Features
                         ↓
                     XGBoost
                         ↓
          ┌──────────────┼────────────────┐
          ↓              ↓                ↓
       SIF Flag       LSR Tags        Cause Tags
          │              │                │
          └──────────────┼────────────────┘
                         ↓
                  Explanation Layer
                         ↓
                  Human HSE Review
                         ↓
                 Confirm / Override
                         ↓
              Active Learning Dataset
                         ↓
                 Model Improvement
                         ↓
             Leadership Trend Dashboard
```

---

# 34. Source-Derived Project Takeaways

### Strongest positive-label signal

**Hi-Po Near Miss** is explicitly defined as a near miss that could realistically have resulted in one or more fatalities.

### Complete cause taxonomy

The OISD cause slide contains **14 categories**, including **Pilferage / miscreant activities**, which should remain available as a cause/contributing-factor tag.

### Investigation / learning provenance

`Case Study` versus `Safety Alert` should be retained as **post-investigation provenance metadata**, not as an initial SIF prediction input, to avoid future-information leakage.

### Strongest domain reasoning signal

**Hazard / energy + failed or absent barrier**.

### Strongest additional classifier

**Standardized incident-cause taxonomy**.

### Strongest explainability concept

Show **which energy/barrier/control signals and report phrases** caused the flag.

### Strongest future data source

Investigation reports + verified causes + corrective actions + investigation / learning provenance.

### Strongest dashboard dimension

**Site × activity × Life-Saving Rule × cause × time**.

### Strongest safety principle

The system should assist HSE officers rather than autonomously make the final safety decision.

### Strongest data-quality principle

Insufficient or novel information should result in **manual review**, not a falsely confident low-risk result.

---

# 35. Important Limitations to Preserve

The source material does **not** establish that:

- OIL's real historical report dataset is already available to the team
- all OIL reports have the same fields
- all reports are in English
- code-mixed Hindi/Assamese reporting definitely occurs at every site
- the exact proposed energy/barrier mapping has been approved by OIL HSE
- any proposed SIF prevalence figure is OIL-specific
- the proposed cost ratio or recall floor has been approved by OIL
- the Nayara Energy presentation is an OIL policy document
- `Case Study` versus `Safety Alert` is a formal severity scale
- investigation / learning provenance is necessarily available at initial report submission

The solution framework itself therefore treats real OIL validation and some field/report-format questions as open dependencies.

The correct MVP posture is:

> **Prototype and validate the architecture on proxy/constructed data, while clearly identifying validation on real OIL data as a required next step.**

---

# 36. Final Project Position

The combined information supports a system that does not merely ask:

> “Does this incident sound dangerous?”

Instead, it should ask:

> **What hazard or energy was present?  
> What safety barrier should have controlled it?  
> Was that barrier present, missing, failed, bypassed or unverified?  
> What Life-Saving Rule does this relate to?  
> What standardized contributing cause is evident?  
> Does the report describe a high-potential / SIF-precursor condition?**

That reasoning can then be converted into:

**classification + structured tags + explanation + human review + longitudinal pattern detection.**

This is the central domain-informed direction to retain while implementing the SIH165 prototype.
