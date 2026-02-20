"""Content-type validation rule.

The user declares the expected data type for a column (e.g. "date", "integer")
and this rule verifies every cell individually.  Complementary to SoftTypingRule
which infers the dominant type statistically.

Supported types: "integer", "decimal", "date", "email", "url".
The rule is dormant when content_type is not configured.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-type validators
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_RE = re.compile(r"^(https?://\S+|www\.[^\s/]+\.\S+)$", re.IGNORECASE)


def _is_integer(value: str) -> bool:
    """Accept bare integers, optionally surrounded by whitespace."""
    try:
        int(value.strip())
        return True
    except ValueError:
        return False


def _is_decimal(value: str) -> bool:
    """Accept integers and decimals; treat French comma as decimal separator."""
    try:
        float(value.strip().replace(",", "."))
        return True
    except ValueError:
        return False


def _is_date(value: str) -> bool:
    """Accept common FR and ISO date formats.

    Accepted patterns (tolerant approach for non-technical users):
      - YYYY-MM-DD  (ISO)
      - DD/MM/YYYY or DD-MM-YYYY  (FR)
      - MM/YYYY  (month/year)
      - YYYY  (year only, 1000–2099)

    Rejected: "32/13/2024" (out-of-range day/month), free text.
    """
    v = value.strip()

    # ISO: YYYY-MM-DD
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        mo, d = int(m.group(2)), int(m.group(3))
        return 1 <= mo <= 12 and 1 <= d <= 31

    # FR: DD/MM/YYYY or DD-MM-YYYY
    m = re.fullmatch(r"(\d{2})[/\-](\d{2})[/\-](\d{4})", v)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        return 1 <= mo <= 12 and 1 <= d <= 31

    # Month/year: MM/YYYY
    m = re.fullmatch(r"(\d{2})/(\d{4})", v)
    if m:
        return 1 <= int(m.group(1)) <= 12

    # Year only: YYYY (restricted to plausible range)
    m = re.fullmatch(r"(\d{4})", v)
    if m:
        return 1000 <= int(m.group(1)) <= 2099

    return False


def _is_email(value: str) -> bool:
    return bool(_EMAIL_RE.match(value.strip()))


def _is_url(value: str) -> bool:
    return bool(_URL_RE.match(value.strip()))


# Maps content_type key → (validator function, FR error message template)
_VALIDATORS: dict[str, tuple] = {
    "integer": (
        _is_integer,
        "Nombre entier attendu, « {value} » n'est pas un nombre entier.",
    ),
    "decimal": (
        _is_decimal,
        "Nombre décimal attendu, « {value} » n'est pas un nombre.",
    ),
    "date": (
        _is_date,
        "Date attendue, « {value} » n'est pas une date reconnue.",
    ),
    "email": (
        _is_email,
        "Adresse e-mail attendue, « {value} » n'est pas une adresse valide.",
    ),
    "url": (
        _is_url,
        "URL attendue, « {value} » n'est pas une URL valide.",
    ),
}


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------


@registry.register
class ContentTypeRule(Rule):
    """Flag cells that do not conform to the declared content_type for a column."""

    rule_id = "generic.content_type"
    name = "Type de contenu"
    default_severity = "ERROR"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        content_type: str | None = config.get("content_type", None)
        if not content_type:
            return []

        validator_entry = _VALIDATORS.get(content_type)
        if validator_entry is None:
            _log.warning(
                "generic.content_type: unknown content_type %r for column %r — rule skipped",
                content_type,
                col,
            )
            return []

        validator, message_template = validator_entry
        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []

        for row_idx, val in df[col].items():
            if pd.isna(val):
                continue
            cell = str(val)
            if cell.strip() == "":
                continue
            if not validator(cell):
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=val,
                        message=message_template.format(value=cell.strip()),
                        suggestion=None,
                    )
                )
        return issues
