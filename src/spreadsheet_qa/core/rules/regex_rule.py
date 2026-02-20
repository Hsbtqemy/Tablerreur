"""Generic per-column regex validation rule.

Flags cells whose value does not fully match the regex declared for the column.
The rule is dormant if no regex is configured.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry

_log = logging.getLogger(__name__)


@registry.register
class RegexRule(Rule):
    """Flag values that do not match the column's declared regex pattern."""

    rule_id = "generic.regex"
    name = "Format (expression régulière)"
    default_severity = "ERROR"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        pattern_str: str | None = config.get("regex", None)
        if not pattern_str:
            return []

        try:
            pattern = re.compile(pattern_str)
        except re.error as exc:
            _log.warning(
                "generic.regex: invalid regex %r for column %r: %s",
                pattern_str,
                col,
                exc,
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
            if not pattern.fullmatch(cell):
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=(
                            f"La valeur « {cell} » ne correspond pas au format attendu "
                            f"({pattern_str})."
                        ),
                        suggestion=None,
                    )
                )
        return issues
