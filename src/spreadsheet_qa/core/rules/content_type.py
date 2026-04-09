"""Content-type validation rule.

The user declares the expected data type for a column (e.g. "date", "integer")
and this rule verifies every cell individually. Complementary to SoftTypingRule
which infers the dominant type statistically.

Supported types:
  - scalar/text: "text", "integer", "decimal", "number", "date"
  - coded values: "boolean", "language", "country"
  - identifiers/links: "identifier", "address", "email", "url"

The rule is dormant when content_type is not configured.
The "text" type accepts any non-empty value (documentation / explicit choice in the UI).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-type validators
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_RE = re.compile(r"^(https?://\S+|www\.[^\s/]+\.\S+)$", re.IGNORECASE)
_DOI_RE = re.compile(r"^10\.\d{4,9}/[^\s]+$", re.IGNORECASE)
_ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", re.IGNORECASE)
_ARK_RE = re.compile(r"^ark:/\d{5}/.+$", re.IGNORECASE)
_ISSN_RE = re.compile(r"^\d{4}-\d{3}[\dX]$", re.IGNORECASE)
_ISBN13_RE = re.compile(r"^97[89][\d\- ]{10,14}$")
_ISBN10_RE = re.compile(r"^[\dX\- ]{10,13}$", re.IGNORECASE)
_BCP47_RE = re.compile(r"^[a-z]{2,3}(-[a-z0-9]{2,8})*$", re.IGNORECASE)
_COUNTRY_RE = re.compile(r"^[a-z]{2}$", re.IGNORECASE)

_BOOLEAN_TRUE_DEFAULT = "oui, o, vrai, true, yes, y, 1, actif, active, enabled"
_BOOLEAN_FALSE_DEFAULT = "non, n, faux, false, no, 0, inactif, inactive, disabled"


def _normalize_identifier_token(value: str) -> str:
    return re.sub(r"[\s\-]", "", value.strip()).upper()


def _is_isbn13_token(value: str) -> bool:
    normalized = _normalize_identifier_token(value)
    return len(normalized) == 13 and normalized.isdigit() and normalized.startswith(("978", "979"))


def _is_isbn10_token(value: str) -> bool:
    normalized = _normalize_identifier_token(value)
    if len(normalized) != 10:
        return False
    return normalized[:9].isdigit() and (normalized[9].isdigit() or normalized[9] == "X")


def _is_integer(value: str, config: dict[str, Any] | None = None) -> bool:
    """Accept bare integers, optionally surrounded by whitespace."""
    try:
        int(value.strip())
        return True
    except ValueError:
        return False


def _is_decimal(value: str, config: dict[str, Any] | None = None) -> bool:
    """Accept integers and decimals; treat French comma as decimal separator."""
    try:
        float(value.strip().replace(",", "."))
        return True
    except ValueError:
        return False


def _is_number(value: str, config: dict[str, Any] | None = None) -> bool:
    """Accept either an integer or a decimal number."""
    return _is_integer(value) or _is_decimal(value)


def _is_date(value: str, config: dict[str, Any] | None = None) -> bool:
    """Accept common FR and ISO date formats.

    Accepted patterns (tolerant approach for non-technical users):
      - YYYY-MM-DD  (ISO)
      - YYYY-MM  (W3C-DTF month precision)
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

    # W3C-DTF partial date: YYYY-MM
    m = re.fullmatch(r"(\d{4})-(\d{2})", v)
    if m:
        return 1 <= int(m.group(2)) <= 12

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


def _is_email(value: str, config: dict[str, Any] | None = None) -> bool:
    return bool(_EMAIL_RE.match(value.strip()))


def _is_url(value: str, config: dict[str, Any] | None = None) -> bool:
    return bool(_URL_RE.match(value.strip()))


def _is_text(value: str, config: dict[str, Any] | None = None) -> bool:
    """Free text: any non-empty string after strip (no structural check)."""
    return bool(value.strip())


def _split_boolean_values(raw: Any, fallback: str) -> set[str]:
    text = str(raw or "").strip()
    source = text or fallback
    return {item.strip().lower() for item in source.split(",") if item.strip()}


def _is_boolean(value: str, config: dict[str, Any] | None = None) -> bool:
    cfg = config or {}
    normalized = value.strip().lower()
    true_values = _split_boolean_values(cfg.get("yes_no_true_values"), _BOOLEAN_TRUE_DEFAULT)
    false_values = _split_boolean_values(cfg.get("yes_no_false_values"), _BOOLEAN_FALSE_DEFAULT)
    return normalized in true_values or normalized in false_values


def _is_identifier(value: str, config: dict[str, Any] | None = None) -> bool:
    v = value.strip()
    return (
        bool(_DOI_RE.match(v))
        or bool(_ORCID_RE.match(v))
        or bool(_ARK_RE.match(v))
        or bool(_ISSN_RE.match(v))
        or (bool(_ISBN13_RE.match(v)) and _is_isbn13_token(v))
        or (bool(_ISBN10_RE.match(v)) and _is_isbn10_token(v))
    )


def _is_language(value: str, config: dict[str, Any] | None = None) -> bool:
    return bool(_BCP47_RE.match(value.strip()))


def _is_country(value: str, config: dict[str, Any] | None = None) -> bool:
    return bool(_COUNTRY_RE.match(value.strip()))


def _is_address(value: str, config: dict[str, Any] | None = None) -> bool:
    return _is_email(value) or _is_url(value)


# Maps content_type key → (validator function, FR error message template)
_VALIDATORS: dict[str, tuple[Callable[[str, dict[str, Any] | None], bool], str]] = {
    "number": (
        _is_number,
        "Nombre attendu, « {value} » n'est pas un nombre reconnu.",
    ),
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
    "boolean": (
        _is_boolean,
        "Booléen attendu, « {value} » n'est pas une valeur vrai/faux reconnue.",
    ),
    "identifier": (
        _is_identifier,
        "Identifiant attendu, « {value} » ne correspond pas à un identifiant reconnu.",
    ),
    "language": (
        _is_language,
        "Code langue attendu, « {value} » n'est pas un code langue reconnu.",
    ),
    "country": (
        _is_country,
        "Code pays attendu, « {value} » n'est pas un code ISO 3166-1 alpha-2 reconnu.",
    ),
    "address": (
        _is_address,
        "Adresse ou lien attendu, « {value} » n'est ni une adresse e-mail ni un lien valide.",
    ),
    "email": (
        _is_email,
        "Adresse e-mail attendue, « {value} » n'est pas une adresse valide.",
    ),
    "url": (
        _is_url,
        "URL attendue, « {value} » n'est pas une URL valide.",
    ),
    "text": (
        _is_text,
        "Texte attendu, « {value} » est vide.",
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
        special: list[str] = config.get("special_values") or []
        special_lower = [sv.lower() for sv in special]
        issues: list[Issue] = []

        for row_idx, val in df[col].items():
            if pd.isna(val):
                continue
            cell = str(val)
            if cell.strip() == "":
                continue
            if special_lower and cell.strip().lower() in special_lower:
                continue  # valeur spéciale acceptée inconditionnellement
            if not validator(cell, config):
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
