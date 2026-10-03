"""
Domain label validator conforming to Register.si registry rules:
- Length: 2 to 63 characters
- Allowed characters: a-z, 0-9, and hyphen (-)
- Hyphen rules:
  * No leading hyphen
  * No trailing hyphen
  * No hyphen at positions 3 AND 4 simultaneously (RFC 5891 / IDNA restriction, e.g. 'ab--cd')
"""

import re
from typing import Tuple

# Standard ASCII LDH pattern (letters, digits, hyphen)
LABEL_REGEX = re.compile(r'^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$')

def validate_si_label(label: str) -> Tuple[bool, str]:
    if not label:
        return False, "Label cannot be empty"

    label = label.lower().strip()

    if len(label) < 2:
        return False, f"Label length {len(label)} is less than registry minimum of 2 characters"

    if len(label) > 63:
        return False, f"Label length {len(label)} exceeds registry maximum of 63 characters"

    if label.startswith("-") or label.endswith("-"):
        return False, "Label cannot start or end with a hyphen"

    # Register.si rule & IDNA standard: hyphens at 3rd and 4th position (1-indexed) are prohibited
    if len(label) >= 4 and label[2] == '-' and label[3] == '-':
        return False, "Hyphens at positions 3 and 4 simultaneously are prohibited"

    if not LABEL_REGEX.match(label):
        return False, "Label contains characters outside allowed set (a-z, 0-9, hyphen)"

    return True, "Valid"
