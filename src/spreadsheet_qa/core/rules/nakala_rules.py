"""NAKALA-specific validation rules.

Implements four Rule subclasses that validate NAKALA metadata fields:

- NakalaCreatedFormatRule  — W3C-DTF date format (YYYY / YYYY-MM / YYYY-MM-DD)
- NakalaDepositTypeRule    — controlled vocabulary (api.nakala.fr/deposittypes)
- NakalaLicenseRule        — controlled vocabulary (api.nakala.fr/licenses)
- NakalaLanguageRule       — controlled vocabulary (api.nakala.fr/languages)

NakalaClient is injected via ``config["_nakala_client"]`` so these rules
remain pure Python and are easily unit-tested without network access.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry

_log = logging.getLogger(__name__)

# W3C-DTF subset accepted by NAKALA: YYYY, YYYY-MM, or YYYY-MM-DD
_CREATED_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


# ---------------------------------------------------------------------------
# NakalaCreatedFormatRule
# ---------------------------------------------------------------------------

@registry.register
class NakalaCreatedFormatRule(Rule):
    rule_id = "nakala.created_format"
    name = "NAKALA created date format"
    default_severity = "ERROR"
    per_column = True

    def check(
        self, df: pd.DataFrame, col: str | None, config: dict[str, Any]
    ) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        severity = Severity(config.get("severity", self.default_severity))
        pattern_str = config.get("regex", None)
        pattern = re.compile(pattern_str) if pattern_str else _CREATED_RE

        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            cell = str(val).strip()
            if not pattern.match(cell):
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=cell,
                        message=(
                            f"Invalid NAKALA date format: {cell!r}. "
                            "Expected YYYY, YYYY-MM, or YYYY-MM-DD."
                        ),
                        suggestion="Use W3C-DTF format, e.g. 2024 or 2024-01-15.",
                    )
                )
        return issues


# ---------------------------------------------------------------------------
# NakalaDepositTypeRule
# ---------------------------------------------------------------------------

@registry.register
class NakalaDepositTypeRule(Rule):
    rule_id = "nakala.deposit_type"
    name = "NAKALA deposit type vocabulary"
    default_severity = "ERROR"
    per_column = True

    def check(
        self, df: pd.DataFrame, col: str | None, config: dict[str, Any]
    ) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        client = config.get("_nakala_client")
        if client is None:
            # No client injected — skip silently (offline / no project)
            return []

        try:
            vocab: list[str] = client.fetch_deposit_types()
        except Exception as exc:
            _log.warning("nakala.deposit_type: could not fetch vocab: %s", exc)
            return []

        if not vocab:
            # Empty vocab means offline — skip to avoid false positives
            return []

        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            cell = str(val).strip()
            if cell not in vocab:
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=cell,
                        message=f"Unknown NAKALA deposit type: {cell!r}.",
                        suggestion="Use a COAR deposit type from api.nakala.fr/vocabularies/deposittypes.",
                    )
                )
        return issues


# ---------------------------------------------------------------------------
# NakalaLicenseRule
# ---------------------------------------------------------------------------

@registry.register
class NakalaLicenseRule(Rule):
    rule_id = "nakala.license"
    name = "NAKALA license vocabulary"
    default_severity = "ERROR"
    per_column = True

    def check(
        self, df: pd.DataFrame, col: str | None, config: dict[str, Any]
    ) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        client = config.get("_nakala_client")
        if client is None:
            return []

        try:
            vocab: list[str] = client.fetch_licenses()
        except Exception as exc:
            _log.warning("nakala.license: could not fetch vocab: %s", exc)
            return []

        if not vocab:
            return []

        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            cell = str(val).strip()
            if cell not in vocab:
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=cell,
                        message=f"Unknown NAKALA license: {cell!r}.",
                        suggestion="Use a license from api.nakala.fr/vocabularies/licenses.",
                    )
                )
        return issues


# ---------------------------------------------------------------------------
# NakalaLanguageRule
# ---------------------------------------------------------------------------

@registry.register
class NakalaLanguageRule(Rule):
    rule_id = "nakala.language"
    name = "NAKALA language vocabulary (RFC5646)"
    default_severity = "WARNING"
    per_column = True

    def check(
        self, df: pd.DataFrame, col: str | None, config: dict[str, Any]
    ) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        client = config.get("_nakala_client")
        if client is None:
            return []

        try:
            vocab: list[str] = client.fetch_languages()
        except Exception as exc:
            _log.warning("nakala.language: could not fetch vocab: %s", exc)
            return []

        if not vocab:
            return []

        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            cell = str(val).strip()
            if cell not in vocab:
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=cell,
                        message=f"Unknown RFC5646 language code: {cell!r}.",
                        suggestion="Use an RFC5646 code from api.nakala.fr/vocabularies/languages.",
                    )
                )
        return issues
