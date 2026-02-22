"""Rule: generic.similar_values

Signals values that are very close to another value in the same column (likely
typos or inconsistent spellings). Dormant by default — must be enabled per
column by setting ``detect_similar_values: true`` in the column configuration.

Algorithm
---------
- Uses ``rapidfuzz.fuzz.ratio`` for pair-wise similarity.
- For columns with more than 500 distinct values, only rare values (count ≤ 3)
  are compared against the full set, keeping the worst-case cost manageable.
- The suggestion returned is the most frequent member of each similar pair.
- One issue is emitted per flagged value (at its first occurrence in the data).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry

try:
    from rapidfuzz import fuzz as _fuzz
    _RAPIDFUZZ_AVAILABLE = True
except ImportError:
    _RAPIDFUZZ_AVAILABLE = False


@registry.register
class SimilarValuesRule(Rule):
    rule_id = "generic.similar_values"
    name = "Valeurs très proches (variantes orthographiques)"
    default_severity = "SUSPICION"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []
        if not _RAPIDFUZZ_AVAILABLE:
            return []

        col_config = config.get("columns", {}).get(col, {})

        # Dormant unless explicitly enabled
        if not col_config.get("detect_similar_values", False):
            return []

        threshold = int(col_config.get("similar_threshold", 85))
        min_distinct = int(col_config.get("similar_min_distinct", 5))

        # Collect non-empty values
        series = df[col].dropna().astype(str)
        series = series[series.str.strip() != ""]
        if series.empty:
            return []

        freq: Counter = Counter(series.tolist())
        distinct = list(freq.keys())

        if len(distinct) < min_distinct:
            return []

        # For large sets, only compare rare values (count ≤ 3) against all others
        large_set = len(distinct) > 500
        candidates = [v for v in distinct if freq[v] <= 3] if large_set else distinct

        # Build flagged map: less-frequent value → (suggestion, score)
        seen_pairs: set[frozenset] = set()
        flagged: dict[str, tuple[str, int]] = {}

        for val in candidates:
            for other in distinct:
                if val == other:
                    continue
                pair: frozenset = frozenset((val, other))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                score = int(_fuzz.ratio(val, other))
                if score >= threshold:
                    # Suggestion = the more frequent of the pair
                    if freq[val] >= freq[other]:
                        suggestion, less_frequent = val, other
                    else:
                        suggestion, less_frequent = other, val
                    # Keep highest-score match for each flagged value
                    if less_frequent not in flagged or score > flagged[less_frequent][1]:
                        flagged[less_frequent] = (suggestion, score)

        if not flagged:
            return []

        # Emit one issue per flagged value at its first occurrence
        issues: list[Issue] = []
        remaining = dict(flagged)  # mutable copy to pop as we find them
        for row_idx in df.index:
            if not remaining:
                break
            raw = df.at[row_idx, col]
            if pd.isna(raw):
                continue
            val = str(raw).strip()
            if val in remaining:
                suggestion, score = remaining.pop(val)
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=Severity.SUSPICION,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=(
                            f"Valeur « {val} » très proche de « {suggestion} » "
                            f"(similarité {score} %) — variante orthographique probable."
                        ),
                        suggestion=suggestion,
                    )
                )

        return issues
