"""
Domain Feature Extractor — S2.3

Implements all 5 feature families from SIH165 Consolidated Domain Intelligence (Section 20):
  A. Energy features
  B. Barrier-status features
  C. Hazard category features
  D. Safety-management features
  E. Equipment / control features

Plus Section 10: Interlock bypass as a high-value dedicated signal.

Core reasoning pattern (Section 2):
    HIGH/RELEVANT ENERGY  +  BARRIER ABSENT/FAILED/BYPASSED/NOT VERIFIED
                         →  SIF-PRECURSOR SIGNAL
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional


# ── A. Energy Terms ───────────────────────────────────────────────────────────

ENERGY_PATTERNS: dict[str, List[str]] = {
    "electrical": [
        r"\belectr(ic|ical|icity)\b", r"\bvolt(age)?\b", r"\b440[Vv]\b",
        r"\b(live|energi[sz]ed)\s+(wire|cable|panel|equipment)\b",
        r"\belectric(al)?\s+(board|panel|shock|flash)\b",
    ],
    "pressure": [
        r"\bpressur(e|ized|ised)\b", r"\bpressurized\s+system\b",
        r"\bPSV\b", r"\bTSV\b", r"\bSDV\b",
        r"\bpump\b.*\buncoupl\b", r"\bhose\b.*\bdepressuris\b",
    ],
    "stored_energy": [
        r"\bstored\s+energy\b", r"\bspring.loaded\b", r"\bactuator\b",
        r"\bpneumatic\b", r"\bhydraulic\b",
    ],
    "mechanical": [
        r"\brotating\b", r"\bmoving\s+part\b", r"\btransmission\s+belt\b",
        r"\bpulley\b", r"\bgear\b", r"\bmechanical\b",
        r"\bdrill(ing)?\s+(rod|bar|machine|bit)\b", r"\bjumbo\b",
        r"\bscaffold(ing)?\b", r"\bwinch\b", r"\bconveyor\b",
        r"\blathe\b", r"\bgrinder\b", r"\bbolt(s)?\b",
    ],
    "gravity_fall": [
        r"\bfall(s|ing)?\b", r"\bgravity\b", r"\bdropped?\b",
        r"\bfalling\s+(object|rock|fragment)\b", r"\bsuspended\s+load\b",
        r"\bcollaps(e|ed|ing)\b", r"\boverturned?\b",
        r"\bslip(ped|ping)?\b", r"\bstruck\b", r"\bimpact(ed)?\b",
        r"\bhit\b", r"\bheight\b", r"\bplatform\b", r"\broof\b",
    ],
    "thermal": [
        r"\bthermal\b", r"\bheat(ed|ing)?\b", r"\bburn(s|ed|ing)?\b",
        r"\bfire\b", r"\bflame\b", r"\bignit(e|ion)\b",
        r"\bhot\s+(work|surface|metal|liquid)\b", r"\bscald\b",
        r"\bweld(ing)?\b", r"\bspark(s)?\b", r"\bmolten\b", r"\bzinc\b",
    ],
    "chemical": [
        r"\bchemical\b", r"\bsolvent\b", r"\bacid\b", r"\bsulphide\b",
        r"\bH2S\b", r"\btoxic\b", r"\bhazardous\s+(substance|material|gas|chemical)\b",
        r"\bexposure\b.*\b(gas|vapou?r|fume|dust)\b",
    ],
    "kinetic_vehicle": [
        r"\bvehicle\b", r"\btruck\b", r"\bforklift\b", r"\bcrane\b",
        r"\blifting\s+(equipment|gear|operation)\b", r"\bexcavator\b",
        r"\bmoving\s+(vehicle|equipment|machinery)\b",
        r"\bmixkret\b", r"\bloader\b",
    ],
    "manual_tools": [
        r"\btool(s)?\b", r"\bpick\b", r"\bchisel\b", r"\bhammer\b",
        r"\bwrench\b", r"\blever\b", r"\bspanner\b", r"\bbarretilla\b",
        r"\bair\s+lance\b", r"\bgrinding\b",
    ],
    "physical_force": [
        r"\bsudden(ly)?\b", r"\bbounced?\b", r"\brecoil\b",
        r"\bheavy\s+(object|load|equipment)\b",
        r"\bweight\b.{0,10}\b(kg|ton)\b",
    ],
    "simops": [
        r"\bSIMOPS\b", r"\bconcurrent\s+(operations|activities|work)\b",
        r"\bsimultaneous\s+operation\b",
    ],
    "confined_space": [
        r"\bconfined\s+space\b", r"\bmanhole\b", r"\bvessel\b.*\bentry\b",
        r"\btank\b.*\bentry\b", r"\basphyxiat\b",
    ],
    "bop": [
        r"\bBOP\b", r"\bblowout\s+preventer\b",
    ],
}

# ── B. Barrier Failure Phrases ────────────────────────────────────────────────

BARRIER_FAILURE_PATTERNS: dict[str, str] = {
    # Isolation / LOTO
    "not_isolated":          r"\bnot\s+isolated\b",
    "isolation_not_verified":r"\bisolation\s+not\s+verified\b",
    "loto_not_performed":    r"\bLOTO\s+not\s+(performed|applied|used|done)\b",
    "not_de_energized":      r"\bnot\s+de.energi[sz]ed\b",
    "re_energized_without":  r"\bre.energi[sz](ed|ing)\b.{0,30}\bnot\s+confirmed\b",
    # Permits
    "no_permit":             r"\bno\s+permit\b",
    "permit_not_obtained":   r"\bpermit\s+not\s+(obtained|issued|signed|raised)\b",
    "without_permit":        r"\bwithout\s+(a\s+)?permit\b",
    # Gas testing
    "no_gas_test":           r"\bno\s+gas\s+test\b",
    "gas_test_not_done":     r"\bgas\s+test\s+not\s+(performed|done|carried\s+out)\b",
    # PPE
    "ppe_not_worn":          r"\bPPE\s+not\s+(worn|used|provided)\b",
    "no_ppe":                r"\bno\s+PPE\b",
    "without_ppe":           r"\bwithout\s+(appropriate\s+)?PPE\b",
    # Physical barriers
    "guardrail_missing":     r"\bguardrail\s+(missing|absent|removed|not\s+installed)\b",
    "harness_not_used":      r"\bharness\s+not\s+(used|worn|attached)\b",
    "no_barricade":          r"\bno\s+barricad(e|ing)\b",
    "barricade_missing":     r"\bbarricad(e|ing)\s+(missing|absent|removed)\b",
    # Authorization
    "authorization_not_obtained": r"\bauthori[sz]ation\s+not\s+(obtained|given|sought)\b",
    "without_authorization": r"\bwithout\s+authoris?ation\b",
    # Fire watch
    "no_fire_watch":         r"\bno\s+fire\s+watch\b",
    "fire_watch_absent":     r"\bfire\s+watch\s+(absent|not\s+present)\b",
    # Ventilation
    "no_ventilation":        r"\bno\s+ventilation\b",
    "inadequate_ventilation":r"\binadequate\s+ventilation\b",
    # Generic bypassed
    "bypassed":              r"\bbypassed?\b",
    "overridden":            r"\boverridden?\b",
}

# ── B2. Interlock Bypass (Section 10 — dedicated high-value signal) ───────────

INTERLOCK_BYPASS_PATTERNS: List[str] = [
    r"\binterlock\s+bypass(ed)?\b",
    r"\bsafety\s+interlock\s+overridden?\b",
    r"\balarm\s+disabled?\b",
    r"\bESD\s+bypass(ed)?\b",
    r"\btrip\s+bypass(ed)?\b",
    r"\bsafety\s+system\s+overridden?\b",
    r"\bprotection\s+disabled?\b",
]

# ── C. Hazard Categories ──────────────────────────────────────────────────────

HAZARD_CATEGORY_PATTERNS: dict[str, List[str]] = {
    "electrical": [r"\belectr(ic|ical)\b"],
    "chemical":   [r"\bchemical\b", r"\bacid\b", r"\bsolvent\b", r"\bH2S\b"],
    "biological": [r"\bbiological\b", r"\bbacteria\b", r"\bvenom(ous)?\b"],
    "physical":   [r"\bphysical\b", r"\bstruck\b", r"\bimpact\b"],
    "mechanical": [r"\bmechanical\b", r"\brotating\b"],
    "environmental": [r"\benvironmental\b", r"\bweather\b", r"\bflood\b"],
}

# ── D. Safety Management Terms ────────────────────────────────────────────────

SAFETY_MGMT_PATTERNS: dict[str, str] = {
    "HIRA":        r"\bHIRA\b",
    "JSA":         r"\bJSA\b",
    "JHA":         r"\bJHA\b",
    "SOP":         r"\bSOP\b",
    "TBT":         r"\bTBT\b|\bToolbox\s+Talk\b",
    "work_permit": r"\bwork\s+permit\b|\bpermit\s+to\s+work\b|\bPTW\b",
    "MOC":         r"\bMOC\b|\bManagement\s+of\s+Change\b",
    "PSSR":        r"\bPSSR\b",
    "LOTO":        r"\bLOTO\b|\blockout\s*/?tagout\b",
}

# ── E. Equipment / Control Terms ──────────────────────────────────────────────

EQUIPMENT_PATTERNS: dict[str, str] = {
    "PSV":          r"\bPSV\b",
    "TSV":          r"\bTSV\b",
    "DCS":          r"\bDCS\b",
    "ESD":          r"\bESD\b",
    "SDV":          r"\bSDV\b",
    "gas_detector": r"\bgas\s+detect(or|ion)\b",
    "H2S_detector": r"\bH2S\s+detect(or|ion)\b",
    "fire_alarm":   r"\bfire\s+alarm\b",
    "smoke_detector": r"\bsmoke\s+detect(or|ion)\b",
    "isolation_valve": r"\bisolation\s+valve\b",
    "blind":        r"\bblind(s)?\b",
}


# ── Output Dataclass ──────────────────────────────────────────────────────────

@dataclass
class FeatureExtractionResult:
    # A
    energy_types:      List[str] = field(default_factory=list)
    has_energy_signal: bool = False
    # B
    barrier_phrases:   List[str] = field(default_factory=list)
    barrier_status:    str = "UNKNOWN"
    has_barrier_failure: bool = False
    # B2
    interlock_bypass_detected: bool = False
    # C
    hazard_categories: List[str] = field(default_factory=list)
    # D
    safety_mgmt_terms: List[str] = field(default_factory=list)
    # E
    equipment_terms:   List[str] = field(default_factory=list)


# ── Extractor ─────────────────────────────────────────────────────────────────

class DomainFeatureExtractor:
    """
    Extracts all 5 domain feature families + interlock bypass signal
    from a safety report narrative.

    Usage:
        extractor = DomainFeatureExtractor()
        result = extractor.extract(text)
    """

    def extract(self, text: str) -> FeatureExtractionResult:
        result = FeatureExtractionResult()
        t = text.lower()

        # A — Energy
        for energy_type, patterns in ENERGY_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, t, re.IGNORECASE):
                    if energy_type not in result.energy_types:
                        result.energy_types.append(energy_type)
                    break
        result.has_energy_signal = len(result.energy_types) > 0

        # B — Barrier failure
        for phrase_key, pattern in BARRIER_FAILURE_PATTERNS.items():
            if re.search(pattern, t, re.IGNORECASE):
                result.barrier_phrases.append(phrase_key)
        result.has_barrier_failure = len(result.barrier_phrases) > 0

        # Derive barrier_status from phrases found
        result.barrier_status = self._derive_barrier_status(result.barrier_phrases)

        # B2 — Interlock bypass (high-value signal)
        for pat in INTERLOCK_BYPASS_PATTERNS:
            if re.search(pat, t, re.IGNORECASE):
                result.interlock_bypass_detected = True
                break

        # C — Hazard categories
        for cat, patterns in HAZARD_CATEGORY_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, t, re.IGNORECASE):
                    if cat not in result.hazard_categories:
                        result.hazard_categories.append(cat)
                    break

        # D — Safety management terms
        for term, pat in SAFETY_MGMT_PATTERNS.items():
            if re.search(pat, t, re.IGNORECASE):
                result.safety_mgmt_terms.append(term)

        # E — Equipment / control terms
        for term, pat in EQUIPMENT_PATTERNS.items():
            if re.search(pat, t, re.IGNORECASE):
                result.equipment_terms.append(term)

        return result

    def _derive_barrier_status(self, phrases: List[str]) -> str:
        """Map detected barrier-failure phrases to a single BarrierStatus value."""
        if not phrases:
            return "UNKNOWN"
        # Priority order: BYPASSED > FAILED > NOT_VERIFIED > MISSING
        bypass_phrases = {"bypassed", "overridden", "loto_not_performed",
                          "interlock_bypass_detected"}
        not_verified   = {"isolation_not_verified", "re_energized_without"}
        missing_phrases = {"no_permit", "no_gas_test", "no_ppe", "guardrail_missing",
                           "no_barricade", "no_fire_watch", "no_ventilation"}

        phrase_set = set(phrases)
        if phrase_set & bypass_phrases:
            return "BYPASSED"
        if phrase_set & not_verified:
            return "NOT_VERIFIED"
        if phrase_set & missing_phrases:
            return "MISSING"
        return "FAILED"


# Singleton instance
extractor = DomainFeatureExtractor()
