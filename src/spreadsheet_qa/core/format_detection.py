"""Heuristics for suggesting a content type / format preset for a column."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Callable

import pandas as pd

from spreadsheet_qa.core.rules.content_type import (
    _is_address,
    _is_boolean,
    _is_country,
    _is_date,
    _is_identifier,
    _is_language,
    _is_number,
)
from spreadsheet_qa.core.rules.pseudo_missing import _DEFAULT_TOKENS as _PSEUDO_MISSING_TOKENS

_TYPE_VALIDATORS: dict[str, Callable[[str], bool]] = {
    "boolean": lambda value: _is_boolean(value, None),
    "identifier": lambda value: _is_identifier(value, None),
    "address": lambda value: _is_address(value, None),
    "country": lambda value: _is_country(value, None),
    "language": lambda value: _is_language(value, None),
    "date": lambda value: _is_date(value, None),
    "number": lambda value: _is_number(value, None),
}

_TYPE_HINTS: dict[str, tuple[str, ...]] = {
    "boolean": ("bool", "flag", "oui", "non", "actif", "active", "enabled"),
    "identifier": ("id", "identifiant", "identifier", "reference", "ref", "doi", "orcid", "isbn", "issn", "ark"),
    "address": ("url", "uri", "site", "web", "mail", "email", "courriel", "lien", "link"),
    "country": ("pays", "country"),
    "language": ("langue", "language", "lang", "locale"),
    "date": ("date", "annee", "year", "created", "creation", "publication", "published"),
    "number": ("nombre", "number", "count", "qty", "quantite", "taille", "size"),
}

_PRESET_TO_TYPE: dict[str, str] = {
    "integer": "number",
    "decimal": "number",
    "positive_int": "number",
    "year": "date",
    "latitude": "number",
    "longitude": "number",
    "yes_no": "boolean",
    "doi": "identifier",
    "orcid": "identifier",
    "ark": "identifier",
    "issn": "identifier",
    "isbn13": "identifier",
    "isbn10": "identifier",
    "email_preset": "address",
    "url": "address",
    "w3cdtf": "date",
    "iso_date": "date",
    "date_fr": "date",
    "lang_iso639": "language",
    "bcp47": "language",
    "country_iso": "country",
}

_TYPE_TO_PRESETS: dict[str, tuple[str, ...]] = {
    "number": ("integer", "decimal", "positive_int", "latitude", "longitude"),
    "boolean": ("yes_no",),
    "identifier": ("doi", "orcid", "ark", "issn", "isbn13", "isbn10"),
    "address": ("email_preset", "url"),
    "country": ("country_iso",),
    "language": ("lang_iso639", "bcp47"),
    "date": ("iso_date", "date_fr", "year", "w3cdtf"),
}

_PRESET_HINTS: dict[str, tuple[str, ...]] = {
    "integer": ("entier", "integer"),
    "decimal": ("decimal", "decim", "float"),
    "positive_int": ("nombre", "count", "qty", "quantite", "taille", "size"),
    "year": ("annee", "year"),
    "latitude": ("lat", "latitude"),
    "longitude": ("lon", "lng", "longitude"),
    "yes_no": ("oui", "non", "bool", "flag"),
    "doi": ("doi",),
    "orcid": ("orcid",),
    "ark": ("ark",),
    "issn": ("issn",),
    "isbn13": ("isbn",),
    "isbn10": ("isbn",),
    "email_preset": ("mail", "email", "courriel"),
    "url": ("url", "uri", "site", "web", "lien", "link"),
    "w3cdtf": ("date", "created", "creation", "publication"),
    "iso_date": ("date", "created", "creation", "publication"),
    "date_fr": ("date",),
    "lang_iso639": ("langue", "language", "lang"),
    "bcp47": ("langue", "language", "locale"),
    "country_iso": ("pays", "country"),
}

_PRESET_SPECIFICITY: dict[str, int] = {
    "iso_date": 5,
    "date_fr": 5,
    "year": 4,
    "doi": 5,
    "orcid": 5,
    "ark": 5,
    "issn": 5,
    "isbn13": 5,
    "isbn10": 5,
    "email_preset": 4,
    "url": 4,
    "lang_iso639": 4,
    "bcp47": 3,
    "country_iso": 4,
    "latitude": 2,
    "longitude": 2,
    "integer": 4,
    "decimal": 3,
    "positive_int": 2,
    "w3cdtf": 1,
    "yes_no": 4,
}

_YEAR_RE = re.compile(r"^\d{4}$")
_INT_RE = re.compile(r"^-?\d+$")
_DECIMAL_RE = re.compile(r"^-?\d+(?:[.,]\d+)?$")
_POSITIVE_INT_RE = re.compile(r"^\d+$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_RE = re.compile(r"^(https?://\S+|www\.[^\s/]+\.\S+)$", re.IGNORECASE)
_DOI_RE = re.compile(r"^10\.\d{4,9}/[^\s]+$", re.IGNORECASE)
_ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", re.IGNORECASE)
_ARK_RE = re.compile(r"^ark:/\d{5}/.+$", re.IGNORECASE)
_ISSN_RE = re.compile(r"^\d{4}-\d{3}[\dX]$", re.IGNORECASE)
_ISBN13_RE = re.compile(r"^97[89][\d\- ]{10,14}$")
_ISBN10_RE = re.compile(r"^[\dX\- ]{10,13}$", re.IGNORECASE)
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_FR_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_W3CDTF_RE = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")
_LANG_ISO639_RE = re.compile(r"(?i)^[a-z]{2,3}$")
_BCP47_RE = re.compile(r"^[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})*$")
_COUNTRY_ISO_RE = re.compile(r"^[A-Z]{2}$")
_LATITUDE_RE = re.compile(r"^-?([0-8]?\d(?:\.\d+)?|90(?:\.0+)?)$")
_LONGITUDE_RE = re.compile(r"^-?(1[0-7]\d(?:\.\d+)?|180(?:\.0+)?|[0-9]{1,2}(?:\.\d+)?)$")
_YES_NO_TRUE = {"oui", "o", "vrai", "true", "yes", "y", "1"}
_YES_NO_FALSE = {"non", "n", "faux", "false", "no", "0"}

_PRESET_DETECTORS: dict[str, Callable[[str], bool]] = {
    "integer": lambda value: bool(_INT_RE.fullmatch(value)),
    "decimal": lambda value: bool(_DECIMAL_RE.fullmatch(value)),
    "positive_int": lambda value: bool(_POSITIVE_INT_RE.fullmatch(value)),
    "year": lambda value: bool(_YEAR_RE.fullmatch(value)) and 1000 <= int(value) <= 2099,
    "latitude": lambda value: bool(_LATITUDE_RE.fullmatch(value)),
    "longitude": lambda value: bool(_LONGITUDE_RE.fullmatch(value)),
    "yes_no": lambda value: value.lower() in (_YES_NO_TRUE | _YES_NO_FALSE),
    "doi": lambda value: bool(_DOI_RE.fullmatch(value)),
    "orcid": lambda value: bool(_ORCID_RE.fullmatch(value)),
    "ark": lambda value: bool(_ARK_RE.fullmatch(value)),
    "issn": lambda value: bool(_ISSN_RE.fullmatch(value)),
    "isbn13": lambda value: bool(_ISBN13_RE.fullmatch(value)),
    "isbn10": lambda value: bool(_ISBN10_RE.fullmatch(value)),
    "email_preset": lambda value: bool(_EMAIL_RE.fullmatch(value)),
    "url": lambda value: bool(_URL_RE.fullmatch(value)),
    "w3cdtf": lambda value: bool(_W3CDTF_RE.fullmatch(value)),
    "iso_date": lambda value: bool(_ISO_DATE_RE.fullmatch(value)),
    "date_fr": lambda value: bool(_DATE_FR_RE.fullmatch(value)),
    "lang_iso639": lambda value: bool(_LANG_ISO639_RE.fullmatch(value)),
    "bcp47": lambda value: bool(_BCP47_RE.fullmatch(value)),
    "country_iso": lambda value: bool(_COUNTRY_ISO_RE.fullmatch(value)),
}


def _normalize_header(column_name: str) -> tuple[str, set[str]]:
    normalized = unicodedata.normalize("NFKD", column_name or "")
    ascii_header = "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()
    ascii_header = re.sub(r"[^a-z0-9]+", " ", ascii_header).strip()
    tokens = {tok for tok in ascii_header.split() if tok}
    return ascii_header, tokens


def _clean_values(series: pd.Series, sample_size: int = 500) -> list[str]:
    values: list[str] = []
    tokens_upper = {token.upper() for token in _PSEUDO_MISSING_TOKENS}
    for raw in series.tolist():
        if pd.isna(raw):
            continue
        text = str(raw).strip()
        if not text:
            continue
        if text.upper() in tokens_upper:
            continue
        values.append(text)
        if len(values) >= sample_size:
            break
    return values


def _header_bonus(ascii_header: str, tokens: set[str], hints: tuple[str, ...]) -> float:
    for hint in hints:
        if hint in tokens:
            return 0.12
        if len(hint) >= 4 and hint in ascii_header:
            return 0.08
    return 0.0


def _type_context_bonus(content_type: str, values: list[str]) -> float:
    if content_type == "country" and values and all(_COUNTRY_ISO_RE.fullmatch(v) for v in values):
        return 0.03
    if content_type == "language":
        if any("-" in v for v in values):
            return 0.04
        if any(v.islower() for v in values if v.isalpha()):
            return 0.02
        if any(len(v) == 3 for v in values if v.isalpha()):
            return 0.02
    if content_type == "date" and any("-" in v or "/" in v for v in values):
        return 0.03
    if content_type == "number" and any("." in v or "," in v for v in values):
        return 0.02
    return 0.0


def _preset_context_bonus(preset: str, values: list[str], header_bonus: float) -> float:
    has_decimal_sep = any("." in v or "," in v for v in values)
    if preset == "decimal" and has_decimal_sep:
        return 0.04
    if preset == "integer" and not has_decimal_sep and all(_INT_RE.fullmatch(v) for v in values):
        return 0.03
    if preset == "positive_int" and all(_POSITIVE_INT_RE.fullmatch(v) for v in values):
        return 0.01
    if preset in {"latitude", "longitude"}:
        return 0.06 if header_bonus > 0 else -0.08
    if preset == "year":
        return 0.03 if header_bonus > 0 else 0.0
    return 0.0


def _rank_candidates(
    values: list[str],
    names: list[str],
    validator_map: dict[str, Callable[[str], bool]],
    hint_map: dict[str, tuple[str, ...]],
    ascii_header: str,
    tokens: set[str],
    context_bonus_fn: Callable[[str, list[str], float], float] | None = None,
) -> list[dict[str, Any]]:
    total = len(values)
    ranked: list[dict[str, Any]] = []
    for name in names:
        validator = validator_map[name]
        matched_examples: list[str] = []
        matched = 0
        for value in values:
            if validator(value):
                matched += 1
                if len(matched_examples) < 3:
                    matched_examples.append(value)
        raw_score = matched / total if total else 0.0
        hint_bonus = _header_bonus(ascii_header, tokens, hint_map.get(name, ()))
        context_bonus = context_bonus_fn(name, values, hint_bonus) if context_bonus_fn else 0.0
        adjusted_score = raw_score + hint_bonus + context_bonus + (_PRESET_SPECIFICITY.get(name, 0) * 0.002)
        ranked.append(
            {
                "name": name,
                "matched": matched,
                "total": total,
                "raw_score": raw_score,
                "adjusted_score": adjusted_score,
                "header_bonus": hint_bonus,
                "examples": matched_examples,
            }
        )
    ranked.sort(key=lambda item: (item["adjusted_score"], item["raw_score"], item["matched"]), reverse=True)
    return ranked


def _type_ranker(name: str, values: list[str], _header_bonus_value: float) -> float:
    return _type_context_bonus(name, values)


def _preset_ranker(name: str, values: list[str], header_bonus_value: float) -> float:
    return _preset_context_bonus(name, values, header_bonus_value)


def _is_ambiguous(best: dict[str, Any], runner_up: dict[str, Any] | None, min_score: float) -> bool:
    if runner_up is None or runner_up["raw_score"] < min_score:
        return False
    close_raw = abs(best["raw_score"] - runner_up["raw_score"]) < 0.05
    close_adjusted = abs(best["adjusted_score"] - runner_up["adjusted_score"]) < 0.05
    same_bonus = abs(best["header_bonus"] - runner_up["header_bonus"]) < 0.05
    return close_raw and close_adjusted and same_bonus


def detect_column_format(
    series: pd.Series,
    column_name: str,
    sample_size: int = 500,
) -> dict[str, Any]:
    """Suggest a content type / format preset from actual column values."""
    values = _clean_values(series, sample_size=sample_size)
    total = len(values)
    if total < 3:
        return {
            "detected": False,
            "content_type": None,
            "format_preset": None,
            "confidence": 0.0,
            "matched": 0,
            "total": total,
            "examples": [],
            "message": "Trop peu de valeurs non vides pour proposer une suggestion fiable.",
        }

    ascii_header, tokens = _normalize_header(column_name)
    type_candidates = _rank_candidates(
        values,
        list(_TYPE_VALIDATORS.keys()),
        _TYPE_VALIDATORS,
        _TYPE_HINTS,
        ascii_header,
        tokens,
        _type_ranker,
    )
    best_type = type_candidates[0]
    runner_type = type_candidates[1] if len(type_candidates) > 1 else None

    if best_type["raw_score"] < 0.85:
        return {
            "detected": False,
            "content_type": None,
            "format_preset": None,
            "confidence": round(best_type["raw_score"], 3),
            "matched": best_type["matched"],
            "total": total,
            "examples": best_type["examples"],
            "message": "Aucune nature dominante suffisamment nette n’a été détectée.",
        }

    if _is_ambiguous(best_type, runner_type, 0.85):
        other_name = runner_type["name"] if runner_type else "une autre nature"
        return {
            "detected": False,
            "content_type": None,
            "format_preset": None,
            "confidence": round(best_type["raw_score"], 3),
            "matched": best_type["matched"],
            "total": total,
            "examples": best_type["examples"],
            "message": (
                f"Analyse ambiguë : la colonne ressemble à la fois à « {best_type['name']} » "
                f"et à « {other_name} »."
            ),
        }

    content_type = best_type["name"]
    preset_candidates = _rank_candidates(
        values,
        list(_TYPE_TO_PRESETS.get(content_type, ())),
        _PRESET_DETECTORS,
        _PRESET_HINTS,
        ascii_header,
        tokens,
        _preset_ranker,
    )
    best_preset = preset_candidates[0] if preset_candidates else None
    runner_preset = preset_candidates[1] if len(preset_candidates) > 1 else None

    # Année civile sur 4 chiffres : year et w3cdtf matchent tous les deux — on privilégie « year ».
    if (
        best_preset
        and runner_preset
        and _is_ambiguous(best_preset, runner_preset, 0.9)
        and {best_preset["name"], runner_preset["name"]} == {"year", "w3cdtf"}
        and values
        and all(_YEAR_RE.fullmatch(v) and 1000 <= int(v) <= 2099 for v in values)
    ):
        year_best = next((p for p in preset_candidates if p["name"] == "year"), None)
        if year_best:
            best_preset, runner_preset = year_best, None

    # Codes langue ISO 639-1 (2 lettres) : lang_iso639 et bcp47 matchent — on privilégie ISO 639.
    if (
        best_preset
        and runner_preset
        and _is_ambiguous(best_preset, runner_preset, 0.9)
        and {best_preset["name"], runner_preset["name"]} == {"lang_iso639", "bcp47"}
        and values
        and all(len(v) == 2 and v.isalpha() and "-" not in v for v in values)
    ):
        iso_best = next((p for p in preset_candidates if p["name"] == "lang_iso639"), None)
        if iso_best:
            best_preset, runner_preset = iso_best, None

    format_preset: str | None = None
    examples = best_type["examples"]
    matched = best_type["matched"]
    confidence = best_type["raw_score"]

    if best_preset and best_preset["raw_score"] >= 0.9 and not _is_ambiguous(best_preset, runner_preset, 0.9):
        format_preset = best_preset["name"]
        examples = best_preset["examples"]
        matched = best_preset["matched"]
        confidence = best_preset["raw_score"]

    if format_preset:
        message = f"Suggestion : {content_type} > {format_preset} ({matched}/{total} valeurs compatibles)."
    else:
        message = f"Suggestion : {content_type} ({matched}/{total} valeurs compatibles, sans sous-format imposé)."

    return {
        "detected": True,
        "content_type": content_type,
        "format_preset": format_preset,
        "confidence": round(confidence, 3),
        "matched": matched,
        "total": total,
        "examples": examples,
        "message": message,
    }
