"""Similar values / typo detection using rapidfuzz.

Only runs on columns with ≤200 distinct non-empty values.
Clusters near-duplicate values (ratio >= threshold) and flags them as
SUSPICION — they may be the same entity spelled differently.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry

try:
    from rapidfuzz import fuzz, process
    _RAPIDFUZZ_AVAILABLE = True
except ImportError:
    _RAPIDFUZZ_AVAILABLE = False


def _cluster_similar(values: list[str], threshold: int) -> list[list[str]]:
    """Return groups of similar strings (each group has >= 2 members)."""
    if not _RAPIDFUZZ_AVAILABLE or len(values) < 2:
        return []

    # Compute pairwise similarity using ratio (full string similarity)
    matrix = process.cdist(values, values, scorer=fuzz.ratio)
    n = len(values)
    visited = [False] * n
    clusters: list[list[str]] = []

    for i in range(n):
        if visited[i]:
            continue
        group = [values[i]]
        visited[i] = True
        for j in range(i + 1, n):
            if not visited[j] and matrix[i][j] >= threshold:
                group.append(values[j])
                visited[j] = True
        if len(group) >= 2:
            clusters.append(group)

    return clusters


@registry.register
class SimilarValuesRule(Rule):
    rule_id = "generic.similar_values"
    name = "Similar / near-duplicate values"
    default_severity = "SUSPICION"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []
        if not _RAPIDFUZZ_AVAILABLE:
            return []

        severity = Severity(config.get("severity", self.default_severity))
        threshold = int(config.get("threshold", 90))
        max_distinct = int(config.get("max_distinct", 200))

        series = df[col].dropna()
        non_empty = series[series.astype(str).str.strip() != ""]
        if non_empty.empty:
            return []

        unique_values = list(non_empty.unique())
        if len(unique_values) > max_distinct:
            return []

        # Run clustering
        clusters = _cluster_similar(unique_values, threshold)
        if not clusters:
            return []

        # Build reverse map: value → cluster members
        suspect_values: dict[str, list[str]] = {}
        for group in clusters:
            for v in group:
                suspect_values[v] = [m for m in group if m != v]

        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            if val in suspect_values:
                similar = suspect_values[val]
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=(
                            f"«{val}» is similar to: "
                            + ", ".join(f"«{s}»" for s in similar[:5])
                        ),
                        extra={"similar_to": similar},
                    )
                )
        return issues
