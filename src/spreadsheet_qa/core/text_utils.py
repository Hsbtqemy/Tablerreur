"""Shared text-processing constants and helpers.

Used by both the core hygiene rules (core/rules/hygiene.py) and the
Find & Fix UI drawer (ui/panels/find_fix_drawer.py) to ensure identical
behavior when detecting and suggesting fixes for common text issues.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Invisible / zero-width code points
# ---------------------------------------------------------------------------

INVISIBLE_RE = re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f\u2028\u2029\u202a-\u202e\ufeff\u00ad]"
)

# ---------------------------------------------------------------------------
# "Smart" / non-standard Unicode characters → ASCII replacements
# ---------------------------------------------------------------------------

UNICODE_SUSPECTS: dict[str, str] = {
    "\u2018": "'",   # left single quotation mark
    "\u2019": "'",   # right single quotation mark
    "\u201c": '"',   # left double quotation mark
    "\u201d": '"',   # right double quotation mark
    "\u2013": "-",   # en dash
    "\u2014": "-",   # em dash
    "\u00a0": " ",   # non-breaking space
}
