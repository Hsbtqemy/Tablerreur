"""Soft typing rule.

If ≥95% of non-empty values in a column (minimum 30 values) match a dominant
type (integer, float, date), the remaining values become SUSPICION issues.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry

_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+[.,]\d+$")
# Simple date pattern: YYYY-MM-DD or YYYY/MM/DD or DD/MM/YYYY
_DATE_RE = re.compile(
    r"^(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})$"
)


def _dominant_type(values: list[str], threshold: float = 0.95) -> str | None:
    """Return the dominant scalar type if enough values match it.

    Args:
        values: Non-empty stripped string values to inspect.
        threshold: Minimum fraction of values that must match to declare a dominant type.
    """
    if not values:
        return None
    checks = {
        "integer": lambda v: bool(_INT_RE.match(v)),
        "float": lambda v: bool(_FLOAT_RE.match(v.replace(",", "."))),
        "date": lambda v: bool(_DATE_RE.match(v)),
    }
    n = len(values)
    for type_name, fn in checks.items():
        matches = sum(1 for v in values if fn(v))
        if matches / n >= threshold:
            return type_name
    return None


@registry.register
class SoftTypingRule(Rule):
    rule_id = "generic.soft_typing"
    name = "Soft typing outlier"
    default_severity = "SUSPICION"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []
        severity = Severity(config.get("severity", self.default_severity))
        min_count = int(config.get("min_count", 30))
        threshold = float(config.get("threshold", 0.95))

        series = df[col].dropna()
        non_empty = [str(v).strip() for v in series if str(v).strip()]

        if len(non_empty) < min_count:
            return []

        dom_type = _dominant_type(non_empty, threshold)
        if dom_type is None:
            return []

        # Build per-type check function
        type_checks = {
            "integer": lambda v: bool(_INT_RE.match(v)),
            "float": lambda v: bool(_FLOAT_RE.match(v.replace(",", "."))),
            "date": lambda v: bool(_DATE_RE.match(v)),
        }
        fn = type_checks[dom_type]

        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if pd.isna(val) or not str(val).strip():
                continue
            v = str(val).strip()
            if not fn(v):
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=(
                            f"Value «{v}» does not match dominant type «{dom_type}» "
                            f"of column «{col}»"
                        ),
                    )
                )
        return issues
