"""Per-column forbidden characters validation rule.

Flags cells that contain one or more characters from the declared
``forbidden_chars`` string.  The rule is dormant if ``forbidden_chars`` is not
configured for the column.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry

# Human-readable names for common special characters
_CHAR_NAMES: dict[str, str] = {
    "\t": "tabulation",
    "\n": "retour à la ligne",
    "\r": "retour chariot",
    ";": "point-virgule",
    "|": "barre verticale",
    '"': "guillemet double",
    "'": "apostrophe",
}


def _char_display(ch: str) -> str:
    """Return a human-readable label for a character."""
    if ch in _CHAR_NAMES:
        return _CHAR_NAMES[ch]
    if ch.isprintable():
        return ch
    return f"U+{ord(ch):04X}"


@registry.register
class ForbiddenCharsRule(Rule):
    """Flag values containing characters explicitly forbidden for the column."""

    rule_id = "generic.forbidden_chars"
    name = "Caractères interdits"
    default_severity = "WARNING"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        forbidden_str: str | None = config.get("forbidden_chars", None)
        if not forbidden_str:
            return []

        forbidden_set = set(forbidden_str)
        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []

        for row_idx, val in df[col].items():
            if pd.isna(val):
                continue
            cell = str(val)
            if cell.strip() == "":
                continue

            found = [ch for ch in forbidden_set if ch in cell]
            if found:
                labels = ", ".join(_char_display(ch) for ch in sorted(found))
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=f"Caractère(s) interdit(s) trouvé(s) : {labels}.",
                    )
                )

        return issues
