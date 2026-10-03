"""
Scoring Engine v2 and Strict Gatekeeper for SI Scout.
Fully explained 0-100 score per candidate across 6 dimensions plus explicit penalties.
Hard-enforces non-negotiable gates for BUY_CANDIDATE tier.
"""

from dataclasses import dataclass, asdict
from enum import Enum
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from si_scout.rdap import RDAPStatus

class CandidateTier(str, Enum):
    BUY_CANDIDATE = "BUY_CANDIDATE"
    MONITOR = "MONITOR"
    AVOID = "AVOID"

@dataclass
class ScoreBreakdown:
    shape_brandability: float       # max 25
    pronounceability_typing: float  # max 15
    semantic_fit_si_ai: float       # max 25
    twin_signals: float             # max 10
    scarcity_manual: float          # max 10
    usability_manual: float         # max 15
    penalties: float                # negative deductions
    total_score: float              # clamped [0, 100]
    rationale_notes: List[str]

@dataclass
class CandidateEvaluation:
    label: str
    domain: str
    tier: CandidateTier
    total_score: float
    breakdown: ScoreBreakdown
    human_rationale: str
    gate_failures: List[str]
    rdap_status: RDAPStatus
    source_type: str = ""

CONSONANT_CLUSTER_REGEX = re.compile(r'[bcdfghjklmnpqrstvwxyz]{3,}')
CORE_AI_TERMS = {
    "agent", "agents", "intel", "intelligence", "neuro", "neural", "cogni", "cognitive",
    "compute", "silicon", "tensor", "model", "models", "robot", "robotics", "swarm",
    "super", "si", "mind", "reason", "logic", "cortex", "synth", "autonomous", "auto"
}

class ScoreEngine:
    def __init__(self):
        pass

    def evaluate(self,
                 label: str,
                 rdap_status: RDAPStatus,
                 is_price_stale: bool,
                 has_trademark_flag: bool,
                 human_rationale: str = "",
                 human_rationale_verified: bool = False,
                 scarcity_manual: float = 0.0,
                 usability_manual: float = 0.0,
                 category: str = "",
                 com_status: str = "UNKNOWN",
                 ai_status: str = "UNKNOWN",
                 trademark_reason: str = "",
                 source_type: str = "",
                 registrar_confirmation: Optional[Dict[str, Any]] = None,
                 now_utc: Optional[datetime] = None) -> CandidateEvaluation:
        label = label.lower().strip()
        domain = f"{label}.si"
        rationale_notes = []
        gate_failures = []

        # 1. Shape & Brandability (max 25)
        shape_pts = 0.0
        label_len = len(label)
        if label_len <= 5:
            shape_pts += 25.0
            rationale_notes.append("Ultra-short length (<=5 chars): +25 pts")
        elif label_len <= 8:
            shape_pts += 20.0
            rationale_notes.append("Short length (6-8 chars): +20 pts")
        elif label_len <= 11:
            shape_pts += 12.0
            rationale_notes.append("Medium length (9-11 chars): +12 pts")
        else:
            shape_pts += 5.0
            rationale_notes.append(f"Long length ({label_len} chars): +5 pts")

        if "-" in label or any(c.isdigit() for c in label):
            shape_pts = max(0.0, shape_pts - 10.0)
            rationale_notes.append("Contains hyphen or digit: -10 pts")

        # 2. Pronounceability & Typing (max 15)
        pronounce_pts = 15.0
        clusters = CONSONANT_CLUSTER_REGEX.findall(label)
        if clusters:
            deduction = min(10.0, len(clusters) * 4.0)
            pronounce_pts -= deduction
            rationale_notes.append(f"Consonant clusters detected: -{deduction} pts")
        
        # Check vowel presence
        vowels = set("aeiouy")
        if not any(c in vowels for c in label) and label_len >= 3:
            pronounce_pts = 0.0
            rationale_notes.append("No vowels detected (poor pronounceability): 0 pts")

        # 3. Semantic Fit to SI / AI Buyer Pool (max 25)
        semantic_pts = 0.0
        matching_terms = [t for t in CORE_AI_TERMS if t in label]
        if matching_terms:
            semantic_pts = min(25.0, 10.0 + (len(matching_terms) * 7.5))
            rationale_notes.append(f"Matches core AI/SI terminology ({', '.join(matching_terms)}): +{semantic_pts} pts")
        elif category in ["intelligence", "agents", "compute", "robotics"]:
            semantic_pts = 15.0
            rationale_notes.append(f"Belongs to priority AI category ({category}): +15 pts")
        else:
            semantic_pts = 5.0
            rationale_notes.append("General technology word: +5 pts")

        # 4. Twin Signal Context (max 10)
        twin_pts = 0.0
        if com_status == "ACTIVE_SITE":
            twin_pts += 7.0
            rationale_notes.append(".com is active site (proven commercial interest): +7 pts")
        elif com_status == "PARKED_OR_FOR_SALE":
            twin_pts += 4.0
            rationale_notes.append(".com is parked for sale: +4 pts")
        elif com_status == "UNREGISTERED":
            twin_pts += 2.0
            rationale_notes.append(".com is unregistered: +2 pts")

        if ai_status == "ACTIVE_SITE":
            twin_pts = min(10.0, twin_pts + 3.0)
            rationale_notes.append(".ai is active site: +3 pts")
        elif ai_status == "PARKED_OR_FOR_SALE":
            twin_pts = min(10.0, twin_pts + 2.0)
            rationale_notes.append(".ai is parked: +2 pts")

        # 5. Scarcity & Usability (Manual Fields)
        scarcity_pts = max(0.0, min(10.0, float(scarcity_manual)))
        usability_pts = max(0.0, min(15.0, float(usability_manual)))
        if scarcity_pts > 0:
            rationale_notes.append(f"Manual scarcity score: +{scarcity_pts} pts")
        if usability_pts > 0:
            rationale_notes.append(f"Manual startup usability: +{usability_pts} pts")

        # 6. Deductions & Penalties
        penalties = 0.0
        if has_trademark_flag:
            penalties += 50.0
            rationale_notes.append(f"Trademark risk penalty: -50 pts ({trademark_reason})")

        subtotal = shape_pts + pronounce_pts + semantic_pts + twin_pts + scarcity_pts + usability_pts
        total_score = max(0.0, min(100.0, subtotal - penalties))

        breakdown = ScoreBreakdown(
            shape_brandability=round(shape_pts, 1),
            pronounceability_typing=round(pronounce_pts, 1),
            semantic_fit_si_ai=round(semantic_pts, 1),
            twin_signals=round(twin_pts, 1),
            scarcity_manual=round(scarcity_pts, 1),
            usability_manual=round(usability_pts, 1),
            penalties=round(penalties, 1),
            total_score=round(total_score, 1),
            rationale_notes=rationale_notes
        )

        # Non-negotiable Gates for BUY_CANDIDATE
        if rdap_status != RDAPStatus.AVAILABLE_CANDIDATE:
            gate_failures.append(f"Domain is not available in registry (RDAP status: {rdap_status.value})")

        if is_price_stale:
            gate_failures.append("Registrar price data is stale (>7 days old)")

        if has_trademark_flag:
            gate_failures.append("Trademark or brand conflict flag present")

        clean_rationale = human_rationale.strip()
        if not clean_rationale or not human_rationale_verified:
            gate_failures.append("Human end-user sentence missing, unverified, or source unknown: requires >=15 words with author='human'")

        if total_score < 60.0:
            gate_failures.append(f"Total score {total_score} below minimum threshold of 60.0")

        # Gate 6: Human registrar checkout confirmation
        if not registrar_confirmation:
            gate_failures.append("Gate 6: Confirmed at a registrar checkout missing (human checkout verification required)")
        else:
            from ui.gates import validate_registrar_confirmation
            is_valid_conf, conf_msg = validate_registrar_confirmation(registrar_confirmation, now_utc=now_utc)
            if not is_valid_conf:
                gate_failures.append(conf_msg)

        # Tier Decision
        if has_trademark_flag or rdap_status in (RDAPStatus.RESERVED,):
            tier = CandidateTier.AVOID
        elif len(gate_failures) == 0:
            tier = CandidateTier.BUY_CANDIDATE
        elif rdap_status in (RDAPStatus.AVAILABLE_CANDIDATE, RDAPStatus.QUARANTINE_PENDING_DELETE):
            tier = CandidateTier.MONITOR
        else:
            tier = CandidateTier.AVOID

        return CandidateEvaluation(
            label=label,
            domain=domain,
            tier=tier,
            total_score=breakdown.total_score,
            breakdown=breakdown,
            human_rationale=clean_rationale,
            gate_failures=gate_failures,
            rdap_status=rdap_status,
            source_type=source_type
        )
