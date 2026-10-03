"""
Offline Pre-Filter for SI Scout.
Performs fast, offline heuristics:
- Ingests Register.si reserved list and allowed rules
- Checks brand & celebrity blocklists
- Evaluates word segmentation & frequency using `wordfreq`
- Scores phonotactics, consonant clusters, length, digits, hyphens
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from wordfreq import zipf_frequency

CONSONANT_CLUSTER_REGEX = re.compile(r'[bcdfghjklmnpqrstvwxyz]{4,}')
VOWELS = set("aeiouy")

class DomainPreFilter:
    def __init__(self, blocklist: Optional[Dict[str, List[str]]] = None,
                 reserved_domains: Optional[Dict[str, str]] = None,
                 tranco_path: Optional[Path] = None):
        self.blocklist = blocklist or {}
        self.reserved_domains = reserved_domains or {}
        
        # Flatten all blocked brand/person terms
        self.blocked_terms = set()
        for cat in ["brands", "public_figures_and_entities", "slovenian_and_governmental"]:
            for term in self.blocklist.get(cat, []):
                self.blocked_terms.add(term.lower().strip())

        # Load Tranco top-100k dominant brands if available
        self.tranco_top100k = set()
        t_path = tranco_path or (Path(__file__).parent / "tranco_top100k.json")
        if t_path.exists():
            try:
                import json
                with open(t_path, "r", encoding="utf-8") as f:
                    self.tranco_top100k = set(json.load(f))
            except Exception:
                pass

    def check_trademark_and_reserved(self, label: str) -> Tuple[bool, str]:
        label_clean = label.lower().strip()
        full_domain = f"{label_clean}.si"

        # 1. Register.si official reserved names check
        if full_domain in self.reserved_domains or label_clean in self.reserved_domains:
            reason = self.reserved_domains.get(full_domain) or self.reserved_domains.get(label_clean)
            return False, f"Official Register.si reserved domain: {reason}"

        # 2. Brand & celebrity blocklist
        for blocked in self.blocked_terms:
            if blocked == label_clean:
                return False, f"Potential trademark risk; professional legal review recommended. Matches blocked mark: '{blocked}'"
            # Substring check for prominent marks longer than 3 chars (e.g. openai in openairesearch)
            if len(blocked) > 3 and blocked in label_clean:
                return False, f"Potential trademark risk; professional legal review recommended. Contains blocked mark: '{blocked}'"

        # 3. Tranco top-100k existing dominant brand check (penalize prominent corporate brands)
        # Exclude generic English dictionary words
        GENERIC_WORDS = {"ai", "si", "agent", "super", "intel", "mind", "model", "cloud", "core", "node", "data", "test", "code", "dev", "flow", "stack", "mesh"}
        if label_clean in self.tranco_top100k and label_clean not in GENERIC_WORDS and len(label_clean) > 4:
            # Check if it's a known popular brand/domain
            return True, f"Tranco top-100k collision: '{label_clean}'"

        return True, ""

    def segment_compound(self, label: str) -> Optional[Tuple[str, str, float, float]]:
        """
        Attempts to split label into two valid English words.
        Returns (w1, w2, freq1, freq2) if split is viable.
        """
        best_split = None
        best_product = 0.0

        for i in range(2, len(label) - 1):
            w1 = label[:i]
            w2 = label[i:]
            f1 = zipf_frequency(w1, 'en')
            f2 = zipf_frequency(w2, 'en')

            # Minimum frequency threshold for a recognized word in English (approx > 2.5)
            if f1 >= 2.5 and f2 >= 2.5:
                score = f1 * f2
                if score > best_product:
                    best_product = score
                    best_split = (w1, w2, f1, f2)

        return best_split

    def evaluate(self, label: str) -> Tuple[bool, str, float]:
        """
        Evaluates a domain label.
        Returns:
          (passed: bool, reason: str, score: float [0-100])
        """
        passed, block_reason = self.check_trademark_and_reserved(label)
        if not passed:
            return False, block_reason, 0.0

        label_len = len(label)
        base_score = 70.0

        # Length adjustments
        if label_len <= 5:
            base_score += 20.0
        elif label_len <= 8:
            base_score += 10.0
        elif label_len > 12:
            base_score -= 25.0
        elif label_len > 10:
            base_score -= 15.0

        # Digits penalty
        if any(c.isdigit() for c in label):
            base_score -= 20.0

        # Hyphen penalty
        if "-" in label:
            base_score -= 15.0

        # Awkward consonant clusters
        clusters = CONSONANT_CLUSTER_REGEX.findall(label)
        if clusters:
            base_score -= (30.0 * len(clusters))

        # Zero vowels penalty (unless standard short abbreviation)
        has_vowels = any(c in VOWELS for c in label)
        if not has_vowels and label_len >= 4:
            base_score -= 30.0

        # Check single word frequency
        single_freq = zipf_frequency(label, 'en')
        if single_freq >= 4.0:
            # Common single dictionary word
            base_score += 15.0
        else:
            # Check two-word compound
            split = self.segment_compound(label)
            if split:
                base_score += 10.0
            else:
                # Neither single common word nor compound
                base_score -= 10.0

        # Plural trailing 's' penalty if awkward
        if label.endswith("s") and not label.endswith("ss") and label_len > 4:
            base_score -= 5.0

        final_score = max(0.0, min(100.0, base_score))
        return True, "Passed pre-filter", round(final_score, 1)
