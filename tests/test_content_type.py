"""Tests for the generic.content_type rule."""

from __future__ import annotations

import logging

import pandas as pd
import pytest

from spreadsheet_qa.core.models import Severity
from spreadsheet_qa.core.rules.content_type import (
    ContentTypeRule,
    _is_date,
    _is_decimal,
    _is_email,
    _is_integer,
    _is_url,
)

rule = ContentTypeRule()


# ---------------------------------------------------------------------------
# Helpers — validator unit tests
# ---------------------------------------------------------------------------


class TestIsInteger:
    def test_positive(self):
        assert _is_integer("42")

    def test_negative(self):
        assert _is_integer("-7")

    def test_zero(self):
        assert _is_integer("0")

    def test_strips_spaces(self):
        assert _is_integer(" 123 ")

    def test_rejects_float(self):
        assert not _is_integer("12.5")

    def test_rejects_text(self):
        assert not _is_integer("abc")

    def test_rejects_mixed(self):
        assert not _is_integer("12a")


class TestIsDecimal:
    def test_float(self):
        assert _is_decimal("3.14")

    def test_negative(self):
        assert _is_decimal("-0.5")

    def test_integer_accepted(self):
        assert _is_decimal("42")

    def test_french_comma(self):
        assert _is_decimal("42,5")
        assert _is_decimal("3,14")

    def test_rejects_text(self):
        assert not _is_decimal("abc")

    def test_rejects_double_dot(self):
        assert not _is_decimal("12.34.56")


class TestIsDate:
    def test_iso(self):
        assert _is_date("2024-01-15")

    def test_fr_slash(self):
        assert _is_date("15/01/2024")

    def test_fr_dash(self):
        assert _is_date("15-01-2024")

    def test_month_year(self):
        assert _is_date("01/2024")

    def test_year_only(self):
        assert _is_date("2024")

    def test_rejects_text(self):
        assert not _is_date("abc")

    def test_rejects_invalid_day(self):
        assert not _is_date("32/01/2024")

    def test_rejects_invalid_month(self):
        assert not _is_date("15/13/2024")

    def test_rejects_mixed_text(self):
        assert not _is_date("hello 2024")

    def test_rejects_year_out_of_range(self):
        assert not _is_date("0099")


class TestIsEmail:
    def test_valid(self):
        assert _is_email("user@example.com")

    def test_subdomain(self):
        assert _is_email("user@mail.example.org")

    def test_rejects_no_at(self):
        assert not _is_email("userexample.com")

    def test_rejects_no_local(self):
        assert not _is_email("@domaine.com")

    def test_rejects_no_domain(self):
        assert not _is_email("user@")

    def test_rejects_no_dot_in_domain(self):
        assert not _is_email("user@domaine")


class TestIsUrl:
    def test_http(self):
        assert _is_url("http://example.com")

    def test_https(self):
        assert _is_url("https://example.com/path?q=1")

    def test_www(self):
        assert _is_url("www.example.com")

    def test_rejects_plain_word(self):
        assert not _is_url("abc")

    def test_rejects_words(self):
        assert not _is_url("juste des mots")


# ---------------------------------------------------------------------------
# ContentTypeRule.check() — per type
# ---------------------------------------------------------------------------


class TestContentTypeRuleInteger:
    def test_valid_no_issue(self):
        df = pd.DataFrame({"N": ["1", "42", "-7"]})
        assert rule.check(df, "N", {"content_type": "integer"}) == []

    def test_invalid_flagged(self):
        df = pd.DataFrame({"N": ["1.5"]})
        issues = rule.check(df, "N", {"content_type": "integer"})
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR
        assert "entier" in issues[0].message

    def test_strips_spaces(self):
        df = pd.DataFrame({"N": [" 42 "]})
        assert rule.check(df, "N", {"content_type": "integer"}) == []

    def test_empty_ignored(self):
        df = pd.DataFrame({"N": ["", None]})
        assert rule.check(df, "N", {"content_type": "integer"}) == []


class TestContentTypeRuleDecimal:
    def test_valid_float_no_issue(self):
        df = pd.DataFrame({"N": ["3.14", "-0.5", "42"]})
        assert rule.check(df, "N", {"content_type": "decimal"}) == []

    def test_french_comma_accepted(self):
        df = pd.DataFrame({"N": ["3,14"]})
        assert rule.check(df, "N", {"content_type": "decimal"}) == []

    def test_invalid_flagged(self):
        df = pd.DataFrame({"N": ["abc"]})
        issues = rule.check(df, "N", {"content_type": "decimal"})
        assert len(issues) == 1
        assert "décimal" in issues[0].message

    def test_empty_ignored(self):
        df = pd.DataFrame({"N": [None, ""]})
        assert rule.check(df, "N", {"content_type": "decimal"}) == []


class TestContentTypeRuleNumber:
    def test_integer_and_decimal_valid(self):
        df = pd.DataFrame({"N": ["42", "3.14", "2,50"]})
        assert rule.check(df, "N", {"content_type": "number"}) == []

    def test_invalid_flagged(self):
        df = pd.DataFrame({"N": ["abc"]})
        issues = rule.check(df, "N", {"content_type": "number"})
        assert len(issues) == 1
        assert "nombre" in issues[0].message.lower()


class TestContentTypeRuleDate:
    def test_iso_valid(self):
        df = pd.DataFrame({"D": ["2024-01-15"]})
        assert rule.check(df, "D", {"content_type": "date"}) == []

    def test_fr_valid(self):
        df = pd.DataFrame({"D": ["15/01/2024"]})
        assert rule.check(df, "D", {"content_type": "date"}) == []

    def test_year_valid(self):
        df = pd.DataFrame({"D": ["2024"]})
        assert rule.check(df, "D", {"content_type": "date"}) == []

    def test_invalid_flagged(self):
        df = pd.DataFrame({"D": ["not-a-date"]})
        issues = rule.check(df, "D", {"content_type": "date"})
        assert len(issues) == 1
        assert "date" in issues[0].message.lower()

    def test_empty_ignored(self):
        df = pd.DataFrame({"D": [None, ""]})
        assert rule.check(df, "D", {"content_type": "date"}) == []


class TestContentTypeRuleEmail:
    def test_valid_no_issue(self):
        df = pd.DataFrame({"E": ["user@example.com"]})
        assert rule.check(df, "E", {"content_type": "email"}) == []

    def test_invalid_flagged(self):
        df = pd.DataFrame({"E": ["pas-un-email"]})
        issues = rule.check(df, "E", {"content_type": "email"})
        assert len(issues) == 1
        assert "e-mail" in issues[0].message

    def test_empty_ignored(self):
        df = pd.DataFrame({"E": [None, ""]})
        assert rule.check(df, "E", {"content_type": "email"}) == []


class TestContentTypeRuleBoolean:
    def test_default_yes_no_values(self):
        df = pd.DataFrame({"B": ["oui", "false", "1", "0"]})
        assert rule.check(df, "B", {"content_type": "boolean"}) == []

    def test_custom_mapping(self):
        df = pd.DataFrame({"B": ["actif", "inactif"]})
        cfg = {
            "content_type": "boolean",
            "yes_no_true_values": "actif",
            "yes_no_false_values": "inactif",
        }
        assert rule.check(df, "B", cfg) == []

    def test_invalid_flagged(self):
        df = pd.DataFrame({"B": ["peut-être"]})
        issues = rule.check(df, "B", {"content_type": "boolean"})
        assert len(issues) == 1
        assert "bool" in issues[0].message.lower()


class TestContentTypeRuleText:
    def test_any_non_empty_accepted(self):
        df = pd.DataFrame({"T": ["hello", "à b c", "123"]})
        assert rule.check(df, "T", {"content_type": "text"}) == []

    def test_empty_cells_ignored(self):
        df = pd.DataFrame({"T": ["", None]})
        assert rule.check(df, "T", {"content_type": "text"}) == []


class TestContentTypeRuleUrl:
    def test_https_valid(self):
        df = pd.DataFrame({"U": ["https://example.com"]})
        assert rule.check(df, "U", {"content_type": "url"}) == []

    def test_www_valid(self):
        df = pd.DataFrame({"U": ["www.example.com"]})
        assert rule.check(df, "U", {"content_type": "url"}) == []

    def test_invalid_flagged(self):
        df = pd.DataFrame({"U": ["pas une url"]})
        issues = rule.check(df, "U", {"content_type": "url"})
        assert len(issues) == 1
        assert "URL" in issues[0].message

    def test_empty_ignored(self):
        df = pd.DataFrame({"U": [None, ""]})
        assert rule.check(df, "U", {"content_type": "url"}) == []


class TestContentTypeRuleIdentifier:
    def test_recognized_identifiers_valid(self):
        df = pd.DataFrame(
            {"I": ["10.1000/xyz123", "0000-0002-1825-0097", "978-1-23-456789-0"]}
        )
        assert rule.check(df, "I", {"content_type": "identifier"}) == []

    def test_invalid_flagged(self):
        df = pd.DataFrame({"I": ["identifiant libre"]})
        issues = rule.check(df, "I", {"content_type": "identifier"})
        assert len(issues) == 1
        assert "identifiant" in issues[0].message.lower()


class TestContentTypeRuleLanguage:
    def test_iso_and_bcp47_valid(self):
        df = pd.DataFrame({"L": ["fr", "fr-FR", "eng"]})
        assert rule.check(df, "L", {"content_type": "language"}) == []

    def test_invalid_flagged(self):
        df = pd.DataFrame({"L": ["français"]})
        issues = rule.check(df, "L", {"content_type": "language"})
        assert len(issues) == 1
        assert "langue" in issues[0].message.lower()


class TestContentTypeRuleCountry:
    def test_alpha2_valid(self):
        df = pd.DataFrame({"C": ["FR", "de"]})
        assert rule.check(df, "C", {"content_type": "country"}) == []

    def test_invalid_flagged(self):
        df = pd.DataFrame({"C": ["France"]})
        issues = rule.check(df, "C", {"content_type": "country"})
        assert len(issues) == 1
        assert "pays" in issues[0].message.lower()


class TestContentTypeRuleAddress:
    def test_email_and_url_valid(self):
        df = pd.DataFrame({"A": ["user@example.com", "https://example.org"]})
        assert rule.check(df, "A", {"content_type": "address"}) == []

    def test_invalid_flagged(self):
        df = pd.DataFrame({"A": ["pas une adresse"]})
        issues = rule.check(df, "A", {"content_type": "address"})
        assert len(issues) == 1
        assert "adresse" in issues[0].message.lower()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestContentTypeRuleEdgeCases:
    def test_no_content_type_rule_inactive(self):
        df = pd.DataFrame({"X": ["anything"]})
        assert rule.check(df, "X", {}) == []

    def test_unknown_content_type_no_crash(self, caplog):
        df = pd.DataFrame({"X": ["value"]})
        with caplog.at_level(logging.WARNING, logger="spreadsheet_qa.core.rules.content_type"):
            issues = rule.check(df, "X", {"content_type": "phone"})
        assert issues == []
        assert "phone" in caplog.text

    def test_severity_override(self):
        df = pd.DataFrame({"N": ["abc"]})
        issues = rule.check(df, "N", {"content_type": "integer", "severity": "WARNING"})
        assert issues[0].severity == Severity.WARNING
