"""
Offline domain label screening engine for Name Lab.
Performs 100% local syntactic, linguistic, and blocklist analysis.
Never queries any network endpoint or registry socket.
"""
from typing import Dict, Any, List
import re
from pathlib import Path

from si_scout.validator import validate_si_label
from si_scout.prefilter import DomainPreFilter
from si_scout.config import load_blocklist, load_reserved_domains


class NameLabScreener:
    def __init__(self):
        try:
            bl = load_blocklist()
            rd = load_reserved_domains()
            self.prefilter = DomainPreFilter(blocklist=bl, reserved_domains=rd)
        except Exception:
            self.prefilter = DomainPreFilter()

    def screen(self, raw_label: str) -> Dict[str, Any]:
        cleaned = (raw_label or "").strip().lower()
        if cleaned.endswith(".si"):
            cleaned = cleaned[:-3]

        # 1. Syntax validation via registry rules
        is_valid_syntax, syntax_reason = validate_si_label(cleaned)

        # 2. Blocklist, reserved domain, and trademark check via prefilter
        passed_tm, tm_reason = self.prefilter.check_trademark_and_reserved(cleaned)
        pf_passed, pf_reason, pf_score = self.prefilter.evaluate(cleaned)

        is_blocked = not passed_tm or not pf_passed
        block_reason = tm_reason if not passed_tm else (pf_reason if not pf_passed else "")
        is_reserved = "reserved" in block_reason.lower()
        is_brand_blocked = not is_reserved and bool(block_reason)

        # 3. Linguistic & pronounceability heuristics
        length = len(cleaned)
        vowels = set("aeiou")
        vowel_count = sum(1 for c in cleaned if c in vowels)
        consonant_count = sum(1 for c in cleaned if c.isalpha() and c not in vowels)
        vowel_ratio = vowel_count / max(1, (vowel_count + consonant_count))

        # Consecutive consonants penalty check
        has_awkward_consonants = bool(re.search(r"[bcdfghjklmnpqrstvwxyz]{4,}", cleaned))

        # Breakdown scoring (0 to 100)
        breakdown = {
            "length_score": 0.0,
            "pronounceability_score": 0.0,
            "keyword_fit_score": 0.0,
            "syntax_valid": is_valid_syntax,
        }

        if not is_valid_syntax or is_blocked:
            overall_score = 0.0
            breakdown["length_score"] = 0.0
            breakdown["pronounceability_score"] = 0.0
            breakdown["keyword_fit_score"] = 0.0
        else:
            # Length score
            if 3 <= length <= 6:
                breakdown["length_score"] = 40.0
            elif 7 <= length <= 9:
                breakdown["length_score"] = 30.0
            elif length == 2 or (10 <= length <= 14):
                breakdown["length_score"] = 15.0
            else:
                breakdown["length_score"] = 5.0

            # Pronounceability
            if 0.30 <= vowel_ratio <= 0.65 and not has_awkward_consonants:
                breakdown["pronounceability_score"] = 35.0
            elif not has_awkward_consonants:
                breakdown["pronounceability_score"] = 20.0
            else:
                breakdown["pronounceability_score"] = 5.0

            # Keyword fit / semantic value
            if pf_passed:
                breakdown["keyword_fit_score"] = round(min(25.0, pf_score * 0.25), 1)
            else:
                breakdown["keyword_fit_score"] = 0.0

            overall_score = round(
                breakdown["length_score"] + breakdown["pronounceability_score"] + breakdown["keyword_fit_score"],
                1
            )

        return {
            "label": cleaned,
            "fqdn": f"{cleaned}.si" if cleaned else "",
            "is_valid_syntax": is_valid_syntax,
            "syntax_reason": syntax_reason,
            "is_blocked": is_blocked,
            "is_reserved": is_reserved,
            "is_brand_blocked": is_brand_blocked,
            "block_reason": block_reason,
            "length": length,
            "vowel_count": vowel_count,
            "consonant_count": consonant_count,
            "vowel_ratio": round(vowel_ratio, 2),
            "has_awkward_consonants": has_awkward_consonants,
            "prefilter_passed": pf_passed,
            "prefilter_reason": pf_reason,
            "breakdown": breakdown,
            "score": overall_score,
            "disclaimer": "Not checked against the registry. Availability must be confirmed at a registrar.",
            "mode_notice": "Offline heuristic evaluation. Zero network queries performed.",
        }


_screener_instance = None

def get_screener() -> NameLabScreener:
    global _screener_instance
    if _screener_instance is None:
        _screener_instance = NameLabScreener()
    return _screener_instance

def screen_label_offline(label: str) -> Dict[str, Any]:
    return get_screener().screen(label)
