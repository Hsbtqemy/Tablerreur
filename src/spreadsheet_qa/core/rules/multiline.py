"""Unexpected multiline cells rule.

If a column is not of kind free_text_long, cells containing newlines
are flagged as WARNING.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry


@registry.register
class UnexpectedMultilineRule(Rule):
    rule_id = "generic.unexpected_multiline"
    name = "Unexpected multiline cell"
    default_severity = "WARNING"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        # Skip if column explicitly allows multiline
        if config.get("multiline_ok", False):
            return []

        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []

        for row_idx, val in df[col].items():
            if not isinstance(val, str) or pd.isna(val):
                continue
            if "\n" in val or "\r" in val:
                fixed = val.replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=f"Unexpected newline in «{col}» (column does not allow multiline)",
                        suggestion=fixed,
                    )
                )
        return issues
