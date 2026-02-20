"""Per-column case validation rule.

Flags cells that do not match the declared casing convention (upper, lower,
title).  The rule is dormant if ``expected_case`` is not configured.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry

_log = logging.getLogger(__name__)

_VALID_CASES = {"upper", "lower", "title"}

_MESSAGES = {
    "upper": "Majuscules attendues. Suggestion : « {suggestion} ».",
    "lower": "Minuscules attendues. Suggestion : « {suggestion} ».",
    "title": "Casse titre attendue. Suggestion : « {suggestion} ».",
}


@registry.register
class CaseRule(Rule):
    """Flag values that do not conform to the declared casing convention."""

    rule_id = "generic.case"
    name = "Casse attendue"
    default_severity = "WARNING"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        expected_case: str | None = config.get("expected_case", None)
        if not expected_case:
            return []

        if expected_case not in _VALID_CASES:
            _log.warning(
                "generic.case: unknown expected_case %r for column %r — rule skipped",
                expected_case,
                col,
            )
            return []

        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []

        for row_idx, val in df[col].items():
            if pd.isna(val):
                continue
            cell = str(val)
            if cell.strip() == "":
                continue

            # Skip cells that contain only digits/symbols (no casing notion)
            if not any(ch.isalpha() for ch in cell):
                continue

            if expected_case == "upper":
                expected = cell.upper()
            elif expected_case == "lower":
                expected = cell.lower()
            else:  # title
                expected = cell.title()

            if cell != expected:
                message = _MESSAGES[expected_case].format(suggestion=expected)
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=message,
                        suggestion=expected,
                    )
                )

        return issues
