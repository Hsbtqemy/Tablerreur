"""Text hygiene rules.

Detects:
- Leading / trailing whitespace
- Multiple consecutive spaces
- Unicode "fancy" characters (curly quotes, em-dashes, non-breaking spaces)
- Invisible / zero-width characters
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry
from spreadsheet_qa.core.text_utils import INVISIBLE_RE as _INVISIBLE_RE
from spreadsheet_qa.core.text_utils import UNICODE_SUSPECTS as _UNICODE_SUSPECTS

# Non-breaking space (local alias used in rule messages)
_NBSP = "\u00a0"

_MULTI_SPACE_RE = re.compile(r"  +")


@registry.register
class LeadingTrailingSpaceRule(Rule):
    rule_id = "generic.hygiene.leading_trailing_space"
    name = "Leading / trailing whitespace"
    default_severity = "WARNING"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []
        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []
        series = df[col]
        for row_idx, val in series.items():
            if not isinstance(val, str) or pd.isna(val):
                continue
            stripped = val.strip()
            if stripped != val:
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=f"Leading or trailing whitespace in «{col}»",
                        suggestion=stripped,
                    )
                )
        return issues


@registry.register
class MultipleSpacesRule(Rule):
    rule_id = "generic.hygiene.multiple_spaces"
    name = "Multiple consecutive spaces"
    default_severity = "WARNING"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []
        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if not isinstance(val, str) or pd.isna(val):
                continue
            if _MULTI_SPACE_RE.search(val):
                fixed = _MULTI_SPACE_RE.sub(" ", val).strip()
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=f"Multiple consecutive spaces in «{col}»",
                        suggestion=fixed,
                    )
                )
        return issues


@registry.register
class UnicodeNormalizationRule(Rule):
    """Flag curly quotes, em/en-dashes, non-breaking spaces, etc."""

    rule_id = "generic.hygiene.unicode_chars"
    name = "Unicode fancy characters"
    default_severity = "SUSPICION"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []
        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if not isinstance(val, str) or pd.isna(val):
                continue
            suspects = [ch for ch in val if ch in _UNICODE_SUSPECTS]
            if suspects:
                fixed = val
                for ch, replacement in _UNICODE_SUSPECTS.items():
                    fixed = fixed.replace(ch, replacement)
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=(
                            f"Non-standard Unicode character(s) in «{col}»: "
                            + ", ".join(
                                f"U+{ord(c):04X} ({unicodedata.name(c, '?')})"
                                for c in set(suspects)
                            )
                        ),
                        suggestion=fixed,
                    )
                )
        return issues


@registry.register
class InvisibleCharsRule(Rule):
    """Flag zero-width spaces and other invisible Unicode code points."""

    rule_id = "generic.hygiene.invisible_chars"
    name = "Invisible / zero-width characters"
    default_severity = "WARNING"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []
        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if not isinstance(val, str) or pd.isna(val):
                continue
            if _INVISIBLE_RE.search(val):
                fixed = _INVISIBLE_RE.sub("", val)
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=f"Invisible/zero-width character(s) in «{col}»",
                        suggestion=fixed,
                    )
                )
        return issues
