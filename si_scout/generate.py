"""
Candidate Domain Generator for SI Scout.
Generates seed words across 8 thematic categories, compounds, prefixes/suffixes, and deduplicates.
Supports 4 core patterns:
- 'single': Single dictionary word
- 'compound': Two-word compound
- 'si_affix': SI-prefixed or suffixed word
- 'prefix_word': Prefix + word (e.g., supercore, deepmind, hyperstack)
"""

from dataclasses import dataclass
from typing import List, Set, Optional
from si_scout.validator import validate_si_label

CATEGORIES = {
    "intelligence": [
        "intel", "mind", "neuro", "neural", "cogni", "thought", "reason", "logic", "brain", 
        "cortex", "nexus", "synth", "omni", "deep", "hyper", "meta", "smart", "vision", "latent", "vector"
    ],
    "agents": [
        "agent", "bot", "swarm", "actor", "auto", "assist", "solver", "worker", 
        "scout", "copilot", "operative", "operator", "delegate", "runner", "pilot", "daemon", "oracle"
    ],
    "compute": [
        "compute", "chip", "silicon", "tensor", "cluster", "node", "core", 
        "wafer", "matrix", "flux", "grid", "super", "qubit", "stack", "server"
    ],
    "infra": [
        "infra", "stack", "pipe", "cloud", "scale", "fabric", "mesh", "wire", 
        "flow", "gate", "stream", "host", "route", "bridge", "relay", "plane", "edge"
    ],
    "robotics": [
        "robot", "droid", "servo", "mech", "cyber", "motion", "motor", "sensor", 
        "actuator", "kinetic", "bionic", "botics"
    ],
    "security": [
        "guard", "safe", "shield", "secure", "cipher", "vault", "audit", 
        "verify", "proof", "defense", "trust", "sentinel", "auth", "lock"
    ],
    "dev_tools": [
        "tool", "kit", "bench", "code", "dev", "test", "forge", "build", 
        "eval", "prompt", "engine", "craft", "studio", "diff", "repo"
    ],
    "research": [
        "research", "lab", "labs", "sci", "math", "model", "data", "query", 
        "vector", "theory", "paper", "graph", "metric"
    ]
}

TECH_PREFIXES = ["super", "hyper", "meta", "ultra", "deep", "open", "cyber", "omni", "neural", "auto", "micro", "nano"]
STEM_WORDS = [
    "core", "mind", "node", "net", "stack", "mesh", "flow", "grid", "cloud", "agent",
    "bot", "lab", "chip", "gate", "trust", "code", "forge", "vault", "proof", "stream",
    "vector", "logic", "tensor", "cortex", "nexus", "plane", "relay", "servo", "shield"
]

SI_AFFIX_WORDS = [
    "agent", "compute", "mind", "model", "guard", "lab", "labs", "core", "flow", "stack",
    "mesh", "logic", "silicon", "tensor", "swarm", "cloud", "robot", "cyber", "vector",
    "data", "host", "forge", "nexus", "chip", "grid", "safe", "node", "vault", "proof", "stream"
]

@dataclass
class GeneratedCandidate:
    label: str
    domain: str
    category: str
    source_type: str  # 'single', 'compound', 'si_affix', 'prefix_word', 'extra'

class DomainGenerator:
    def __init__(self, tld: str = "si"):
        self.tld = tld

    def generate(self,
                 extra_names: Optional[List[str]] = None,
                 max_count: Optional[int] = None,
                 pattern_filter: Optional[List[str]] = None,
                 batch: int = 1) -> List[GeneratedCandidate]:
        candidates: List[GeneratedCandidate] = []
        seen_labels: Set[str] = set()

        def add_candidate(label: str, category: str, source_type: str):
            clean = label.strip().lower()
            if clean in seen_labels:
                return
            is_valid, _ = validate_si_label(clean)
            if not is_valid:
                return
            if pattern_filter and source_type not in pattern_filter:
                return
            seen_labels.add(clean)
            candidates.append(GeneratedCandidate(
                label=clean,
                domain=f"{clean}.{self.tld}",
                category=category,
                source_type=source_type
            ))

        # 1. Process user-supplied extra names
        if extra_names:
            for extra in extra_names:
                add_candidate(extra, "user_specified", "extra")

        # 2. Single words
        for cat_name, words in CATEGORIES.items():
            for word in words:
                add_candidate(word, cat_name, "single")

        # 3. SI-prefixed and suffixed words
        for kw in SI_AFFIX_WORDS:
            add_candidate(f"si{kw}", "si_branded", "si_affix")
            add_candidate(f"{kw}si", "si_branded", "si_affix")

        # 4. Prefix + word patterns
        for prefix in TECH_PREFIXES:
            for stem in STEM_WORDS:
                add_candidate(f"{prefix}{stem}", "prefix_word", "prefix_word")

        # 5. Two-word compounds between high-value categories
        intel_words = CATEGORIES["intelligence"]
        agent_words = CATEGORIES["agents"]
        infra_words = CATEGORIES["infra"] + CATEGORIES["compute"]
        sec_words = CATEGORIES["security"]
        dev_words = CATEGORIES["dev_tools"]
        res_words = CATEGORIES["research"]

        if batch == 1:
            for w1 in intel_words[:8]:
                for w2 in agent_words[:8]:
                    add_candidate(f"{w1}{w2}", "intelligence_agents", "compound")
                    add_candidate(f"{w2}{w1}", "intelligence_agents", "compound")

            for w1 in infra_words[:8]:
                for w2 in dev_words[:8]:
                    add_candidate(f"{w1}{w2}", "infra_devtools", "compound")

            for w1 in sec_words[:8]:
                for w2 in agent_words[:8]:
                    add_candidate(f"{w1}{w2}", "security_agents", "compound")

            for w1 in intel_words[:6]:
                for w2 in infra_words[:6]:
                    add_candidate(f"{w1}{w2}", "intel_infra", "compound")

            for w1 in res_words[:6]:
                for w2 in infra_words[:6]:
                    add_candidate(f"{w1}{w2}", "research_infra", "compound")
        elif batch == 2:
            # Batch 2 for adaptive round: deeper combinations
            for w1 in intel_words[8:16]:
                for w2 in agent_words[:10]:
                    add_candidate(f"{w1}{w2}", "intelligence_agents", "compound")
                    add_candidate(f"{w2}{w1}", "intelligence_agents", "compound")
            for w1 in infra_words[8:16]:
                for w2 in dev_words[:10]:
                    add_candidate(f"{w1}{w2}", "infra_devtools", "compound")
            for w1 in sec_words[8:14]:
                for w2 in agent_words[:10]:
                    add_candidate(f"{w1}{w2}", "security_agents", "compound")
            for prefix in ["neural", "omni", "smart", "vision"]:
                for stem in STEM_WORDS:
                    add_candidate(f"{prefix}{stem}", "prefix_word", "prefix_word")

        # Interleave compounds and prefix_words to ensure balanced pattern sampling
        extras = [c for c in candidates if c.source_type == "extra"]
        singles = [c for c in candidates if c.source_type == "single"]
        si_affixes = [c for c in candidates if c.source_type == "si_affix"]
        compounds = [c for c in candidates if c.source_type == "compound"]
        prefix_words = [c for c in candidates if c.source_type == "prefix_word"]

        interleaved_pairs = []
        max_len = max(len(compounds), len(prefix_words))
        for i in range(max_len):
            if i < len(compounds):
                interleaved_pairs.append(compounds[i])
            if i < len(prefix_words):
                interleaved_pairs.append(prefix_words[i])

        ordered = extras + singles + si_affixes + interleaved_pairs
        if max_count and max_count > 0:
            return ordered[:max_count]

        return ordered
