"""Duplicate detection rules.

- DuplicateRowsRule: flags rows that are identical to another row → WARNING
- UniqueColumnRule: flags duplicates in a column marked as `unique` → ERROR
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry


@registry.register
class DuplicateRowsRule(Rule):
    """Detect fully duplicate rows in the dataset."""

    rule_id = "generic.duplicate_rows"
    name = "Duplicate rows"
    default_severity = "WARNING"
    per_column = False  # operates on the whole DataFrame

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if df.empty:
            return []
        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []

        dup_mask = df.duplicated(keep="first")
        dup_rows = df.index[dup_mask].tolist()

        for row_idx in dup_rows:
            issues.append(
                Issue.create(
                    rule_id=self.rule_id,
                    severity=severity,
                    row=int(row_idx),
                    col="__row__",  # sentinel for "whole row"
                    original=None,
                    message=f"Row {row_idx + 1} is a duplicate of an earlier row",
                )
            )
        return issues


@registry.register
class UniqueColumnRule(Rule):
    """Detect duplicate values in a column that should be unique."""

    rule_id = "generic.unique_column"
    name = "Unique column violation"
    default_severity = "ERROR"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []
        # Only run if the column is marked unique in the template config
        if not config.get("unique", False):
            return []

        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []

        series = df[col].dropna()
        dup_mask = series.duplicated(keep="first")
        dup_indices = series.index[dup_mask].tolist()

        for row_idx in dup_indices:
            val = df.at[row_idx, col]
            issues.append(
                Issue.create(
                    rule_id=self.rule_id,
                    severity=severity,
                    row=int(row_idx),
                    col=col,
                    original=val,
                    message=f"Duplicate value «{val}» in unique column «{col}»",
                )
            )
        return issues
