"""Rare value detection (config-driven).

Dormant unless ``detect_rare_values: true`` is set for the column in the
template or user config.

Config keys
-----------
detect_rare_values : bool
    Must be True to activate this rule (default: False → rule skipped).
rare_threshold : int
    Values whose (case-insensitive) frequency is ≤ this threshold are
    flagged.  Default: 1 (flags only hapax-style values).
rare_min_total : int
    Minimum number of non-empty values required in the column before
    the analysis runs.  Default: 10.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry


@registry.register
class RareValuesRule(Rule):
    rule_id = "generic.rare_values"
    name = "Valeur rare / possible erreur de saisie"
    default_severity = "SUSPICION"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        # Dormant unless explicitly activated per column
        if not config.get("detect_rare_values", False):
            return []
        if col is None or col not in df.columns:
            return []

        severity = Severity(config.get("severity", self.default_severity))
        threshold = int(config.get("rare_threshold", 1))
        min_total = int(config.get("rare_min_total", 10))

        series = df[col].dropna()
        non_empty = series[series.astype(str).str.strip() != ""]
        total = len(non_empty)

        if total < min_total:
            return []

        # Case-insensitive frequency counts (strip + lower)
        normalised = non_empty.astype(str).str.strip().str.lower()
        freq = normalised.value_counts()

        # Build set of normalised forms that are rare (≤ threshold)
        rare_normalised = set(freq[freq <= threshold].index)
        if not rare_normalised:
            return []

        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            norm = str(val).strip().lower()
            if norm in rare_normalised:
                n = int(freq[norm])
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=(
                            f"Valeur « {val} » n'apparaît que {n} fois sur {total}"
                            " (possible erreur de saisie)."
                        ),
                    )
                )
        return issues
