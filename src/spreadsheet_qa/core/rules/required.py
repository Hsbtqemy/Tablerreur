"""Per-column required-value validation rule.

Flags cells that are empty or contain a pseudo-missing token when the column
is declared as required. The rule is dormant if ``required`` is not set or
is False for the column.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry

# Default set of values treated as "empty" (in addition to truly empty strings)
_DEFAULT_EMPTY_TOKENS: list[str] = [
    "", "NA", "N/A", "n/a", "null", "NULL", "None",
    "-", ".", "?", "#N/A", "#REF!", "#VALEUR!",
]


@registry.register
class RequiredRule(Rule):
    """Flag missing values in columns declared as required."""

    rule_id = "generic.required"
    name = "Valeur obligatoire"
    default_severity = "ERROR"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        if not config.get("required", False):
            return []

        empty_tokens: list[str] = config.get("empty_tokens", _DEFAULT_EMPTY_TOKENS)
        empty_set = set(empty_tokens)
        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []

        for row_idx, val in df[col].items():
            if pd.isna(val):
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message="Valeur obligatoire manquante.",
                    )
                )
                continue

            cell = str(val)
            if cell.strip() == "" or cell in empty_set:
                if cell.strip() == "":
                    message = "Valeur obligatoire manquante."
                else:
                    message = f"Valeur obligatoire manquante (« {cell} » est considéré comme vide)."
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=message,
                    )
                )

        return issues
