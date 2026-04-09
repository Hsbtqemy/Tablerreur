"""Tests for format auto-detection heuristics."""

from __future__ import annotations

import pandas as pd
import pytest

from spreadsheet_qa.core.format_detection import detect_column_format


def test_detect_integer_number():
    series = pd.Series(["1", "2", "3", "42"])
    data = detect_column_format(series, "entier")
    assert data["detected"] is True
    assert data["content_type"] == "number"
    assert data["format_preset"] == "integer"


def test_detect_positive_int_for_quantity_column():
    series = pd.Series(["1", "2", "3", "42"])
    data = detect_column_format(series, "quantite")
    assert data["detected"] is True
    assert data["content_type"] == "number"
    assert data["format_preset"] == "positive_int"


def test_detect_year_from_header_hint():
    series = pd.Series(["2020", "2021", "2022", "2023"])
    data = detect_column_format(series, "annee_publication")
    assert data["detected"] is True
    assert data["content_type"] == "date"
    assert data["format_preset"] == "year"


def test_detect_email_address():
    series = pd.Series(["a@example.org", "b@example.org", "c@example.org"])
    data = detect_column_format(series, "courriel_contact")
    assert data["detected"] is True
    assert data["content_type"] == "address"
    assert data["format_preset"] == "email_preset"


def test_detect_boolean_yes_no_without_boolean_header():
    series = pd.Series(["oui", "non", "oui", "non"])
    data = detect_column_format(series, "statut")
    assert data["detected"] is True
    assert data["content_type"] == "boolean"
    assert data["format_preset"] == "yes_no"
    assert data["candidates"][0]["content_type"] == "boolean"
    assert data["candidates"][0]["format_preset"] == "yes_no"


def test_detect_isbn13_preset():
    series = pd.Series(["9781234567890", "9791234567891", "9781234567892"])
    data = detect_column_format(series, "isbn")
    assert data["detected"] is True
    assert data["content_type"] == "identifier"
    assert data["format_preset"] == "isbn13"
    assert data["candidates"][0]["format_preset"] == "isbn13"


def test_ambiguous_years_without_hint_return_no_detection():
    series = pd.Series(["2020", "2021", "2022", "2023"])
    data = detect_column_format(series, "code")
    assert data["detected"] is False
    assert len(data["candidates"]) >= 2
    assert data["candidates"][0]["content_type"] == "date"
    assert any(candidate["content_type"] == "number" for candidate in data["candidates"])


def test_detect_language_vs_country_with_header_hint():
    series = pd.Series(["fr", "en", "de", "it"])
    data = detect_column_format(series, "langue")
    assert data["detected"] is True
    assert data["content_type"] == "language"
    assert data["format_preset"] == "lang_iso639"


@pytest.mark.parametrize(
    ("column_name", "values", "expected_type", "expected_preset"),
    [
        ("doi_reference", ["10.1234/alpha", "10.5281/zenodo.42", "10.1000/test"], "identifier", "doi"),
        ("orcid_auteur", ["0000-0002-1825-0097", "0000-0001-5109-3700", "0000-0003-1234-567X"], "identifier", "orcid"),
        ("ark_notice", ["ark:/67375/abc123", "ark:/12345/xyz", "ark:/99999/test"], "identifier", "ark"),
        ("issn_revue", ["0317-8471", "2434-561X", "1234-567X"], "identifier", "issn"),
        ("isbn", ["9781234567890", "9791234567891", "978-1-23-456789-0"], "identifier", "isbn13"),
        ("isbn", ["0123456789", "012345678X", "0-12-345678-9"], "identifier", "isbn10"),
        ("latitude", ["48.8566", "43.2965", "-21.1151"], "number", "latitude"),
        ("longitude", ["2.3522", "5.3698", "55.5364"], "number", "longitude"),
        ("date_publication", ["2024", "2023", "2022"], "date", "year"),
        ("date_publication", ["2024-01", "2024-02", "2025-03"], "date", "w3cdtf"),
        ("date_publication", ["2024-01-15", "2024-02-01", "2025-03-31"], "date", "iso_date"),
        ("date_fr", ["15/01/2024", "01/12/1999", "31/03/2025"], "date", "date_fr"),
        ("statut", ["0", "1", "1", "0"], "boolean", "yes_no"),
        ("statut", ["actif", "inactif", "actif", "inactif"], "boolean", "yes_no"),
    ],
)
def test_detect_real_world_presets(column_name, values, expected_type, expected_preset):
    data = detect_column_format(pd.Series(values), column_name)
    assert data["detected"] is True
    assert data["content_type"] == expected_type
    assert data["format_preset"] == expected_preset
    assert data["candidates"][0]["content_type"] == expected_type
    assert data["candidates"][0]["format_preset"] == expected_preset
