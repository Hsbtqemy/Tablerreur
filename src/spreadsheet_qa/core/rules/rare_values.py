"""Rare (hapax) value detection.

Treats a column as categorical if:
  distinct_count <= 50  AND  distinct_count / non_empty_count <= 0.2

Within such columns, values that appear only once (hapax) are flagged as
SUSPICION (they may be typos or data entry errors).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry


@registry.register
class RareValuesRule(Rule):
    rule_id = "generic.rare_values"
    name = "Rare / hapax value"
    default_severity = "SUSPICION"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []
        severity = Severity(config.get("severity", self.default_severity))
        max_distinct = int(config.get("max_distinct", 50))
        max_ratio = float(config.get("max_ratio", 0.2))

        series = df[col].dropna()
        non_empty = series[series.astype(str).str.strip() != ""]
        if non_empty.empty:
            return []

        value_counts = non_empty.value_counts()
        distinct = len(value_counts)
        total = len(non_empty)

        # Only treat as categorical if thresholds are met
        if distinct > max_distinct or (distinct / total) > max_ratio:
            return []

        # Find hapax values (count == 1)
        hapax_values = set(value_counts[value_counts == 1].index)
        if not hapax_values:
            return []

        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            if val in hapax_values:
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=(
                            f"Rare value «{val}» appears only once in categorical column «{col}» "
                            f"({distinct} distinct values)"
                        ),
                    )
                )
        return issues
