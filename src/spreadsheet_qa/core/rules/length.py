"""Per-column length validation rule.

Flags cells that are shorter than min_length or longer than max_length.
The rule is dormant if neither bound is configured.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry


@registry.register
class LengthRule(Rule):
    """Flag values that fall outside the declared min/max length for a column."""

    rule_id = "generic.length"
    name = "Longueur de valeur"
    default_severity = "WARNING"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        min_length: int | None = config.get("min_length", None)
        max_length: int | None = config.get("max_length", None)

        if min_length is None and max_length is None:
            return []

        # Normalize to int if provided (YAML may deliver them as int already)
        if min_length is not None:
            min_length = int(min_length)
        if max_length is not None:
            max_length = int(max_length)

        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []

        for row_idx, val in df[col].items():
            if pd.isna(val):
                continue
            cell = str(val)
            if cell.strip() == "":
                continue
            n = len(cell)
            if min_length is not None and n < min_length:
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=(
                            f"Valeur trop courte ({n} caractère{'s' if n > 1 else ''}, "
                            f"minimum {min_length})."
                        ),
                        suggestion=None,
                    )
                )
            elif max_length is not None and n > max_length:
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=(
                            f"Valeur trop longue ({n} caractères, maximum {max_length})."
                        ),
                        suggestion=None,
                    )
                )
        return issues
