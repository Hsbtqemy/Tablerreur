"""Tests for format auto-detection heuristics."""

from __future__ import annotations

import pandas as pd

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


def test_ambiguous_years_without_hint_return_no_detection():
    series = pd.Series(["2020", "2021", "2022", "2023"])
    data = detect_column_format(series, "code")
    assert data["detected"] is False


def test_detect_language_vs_country_with_header_hint():
    series = pd.Series(["fr", "en", "de", "it"])
    data = detect_column_format(series, "langue")
    assert data["detected"] is True
    assert data["content_type"] == "language"
    assert data["format_preset"] == "lang_iso639"
