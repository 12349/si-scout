"""
SI Scout: Canonical Six Screening Gates Definition.
Shared across UI Gate Simulator, Story Mode, and Documentation.
"""

SIX_GATES = [
    {
        "id": 1,
        "name": "not in registry",
        "title": "Gate 1: Not in Registry",
        "short_desc": "404 response from authoritative Register.si RDAP",
        "full_desc": "The authoritative Register.si RDAP query returned HTTP 404 (not found). Note: this only proves no active delegation record exists; it does not verify registrar retail availability.",
        "badge": "404 response",
        "rule": "Authoritative registry RDAP returned HTTP 404",
    },
    {
        "id": 2,
        "name": "fresh prices (7 days)",
        "title": "Gate 2: Fresh Prices (7 Days)",
        "short_desc": "Registrar fee snapshot <= 7 days old",
        "full_desc": "Active registrar fee snapshots must be verified within the past 7 days. Stale price quotes block candidate status to prevent hidden renewal fee inflation.",
        "badge": "Snapshot <= 7 days",
        "rule": "Registrar fee snapshot <= 7 days old",
    },
    {
        "id": 3,
        "name": "fresh check (60 minutes)",
        "title": "Gate 3: Fresh Check (60 Minutes)",
        "short_desc": "Registry availability tested <= 60 minutes ago",
        "full_desc": "A domain check timestamp older than 60 minutes is considered stale for evaluation decisions. Competing registrations require recent verification.",
        "badge": "Tested <= 60 mins",
        "rule": "Registry availability tested <= 60 minutes ago",
    },
    {
        "id": 4,
        "name": "human rationale (15 words)",
        "title": "Gate 4: Human Rationale (15 Words)",
        "short_desc": ">= 15 words written by human operator, not AI",
        "full_desc": "Requires a human operator to enter a specific justification sentence (>= 15 words) and confirm human authorship. Auto-generated rationale is blocked.",
        "badge": ">= 15 words, human",
        "rule": ">= 15 words written by human operator, not AI",
    },
    {
        "id": 5,
        "name": "budget fit",
        "title": "Gate 5: Budget Fit",
        "short_desc": "Fits within holding term budget ceiling",
        "full_desc": "Total carry costs (registration plus renewals across planned holding years) must fit within the user's allocated budget ceiling after reserve deductions.",
        "badge": "Fits holding term cap",
        "rule": "Fits within holding term budget ceiling",
    },
    {
        "id": 6,
        "name": "registrar checkout confirmation (60 minutes)",
        "title": "Gate 6: Registrar Checkout Confirmation (60 Minutes)",
        "short_desc": "Confirmed available at accredited registrar cart <= 60 minutes ago",
        "full_desc": "A human operator must manually test the domain in an accredited registrar's shopping cart, recording the registrar name, UTC timestamp, and observed availability. Expires after 60 minutes.",
        "badge": "Accredited registrar <= 60m",
        "rule": "Confirmed available at accredited registrar cart <= 60 minutes ago",
    },
]
