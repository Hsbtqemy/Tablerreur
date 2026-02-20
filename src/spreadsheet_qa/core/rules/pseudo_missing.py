"""Pseudo-missing value detection.

Flags cells containing tokens that represent "no value" but are not actually
empty: NA, N/A, NULL, -, ?, n/a, null, none, etc.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry

_DEFAULT_TOKENS = {"NA", "N/A", "NULL", "null", "n/a", "na", "-", "?", "none", "None", "#N/A"}


@registry.register
class PseudoMissingRule(Rule):
    rule_id = "generic.pseudo_missing"
    name = "Pseudo-missing value tokens"
    default_severity = "WARNING"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []
        severity = Severity(config.get("severity", self.default_severity))
        tokens: set[str] = set(config.get("tokens", _DEFAULT_TOKENS))
        issues: list[Issue] = []

        for row_idx, val in df[col].items():
            if not isinstance(val, str) or pd.isna(val):
                continue
            stripped = val.strip()
            if stripped in tokens:
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=(
                            f"Pseudo-missing value «{stripped}» in «{col}» — "
                            "consider using an empty cell instead"
                        ),
                        suggestion=None,  # no automated fix (ambiguous)
                    )
                )
        return issues
