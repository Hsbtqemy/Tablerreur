"""Tests for special_values bypass in regex_rule and content_type.

Covers:
  - "Inconnue" in nakala:created → no regex error
  - "inconnue" (lowercase) → no error (case-insensitive)
  - "2024-01-15" → no error (valid W3C-DTF)
  - "n'importe quoi" → error (neither regex nor special_values)
  - "Anonyme" in nakala:creator → no regex error
  - "Dupont, Jean" → no error (valid regex)
  - generic.regex rule respects special_values
  - generic.content_type rule respects special_values
"""
from __future__ import annotations

import pandas as pd
import pytest

from spreadsheet_qa.core.engine import ValidationEngine
from spreadsheet_qa.core.rules.regex_rule import RegexRule
from spreadsheet_qa.core.rules.content_type import ContentTypeRule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_df(col: str, values: list[str]) -> pd.DataFrame:
    return pd.DataFrame({col: pd.array(values, dtype="object")})


def _issues_for_regex(col: str, values: list[str], pattern: str, special_values: list[str]) -> list:
    df = _make_df(col, values)
    rule = RegexRule()
    config = {"regex": pattern, "special_values": special_values}
    return rule.check(df, col, config)


def _issues_for_content_type(col: str, values: list[str], content_type: str,
                              special_values: list[str]) -> list:
    df = _make_df(col, values)
    rule = ContentTypeRule()
    config = {"content_type": content_type, "special_values": special_values}
    return rule.check(df, col, config)


# ---------------------------------------------------------------------------
# Tests generic.regex avec special_values
# ---------------------------------------------------------------------------

def test_regex_special_value_bypasses_check():
    """'Anonyme' in a column with regex should produce no issue."""
    issues = _issues_for_regex(
        col="nakala:creator",
        values=["Anonyme"],
        pattern=r"^[^,]+,\s*.+",
        special_values=["Anonyme"],
    )
    assert issues == [], "Anonyme should be accepted via special_values"


def test_regex_special_value_case_insensitive():
    """special_values check is case-insensitive: 'ANONYME' and 'anonyme' both bypass."""
    for variant in ["ANONYME", "anonyme", "Anonyme", "AnOnYmE"]:
        issues = _issues_for_regex(
            col="creator",
            values=[variant],
            pattern=r"^[^,]+,\s*.+",
            special_values=["Anonyme"],
        )
        assert issues == [], f"'{variant}' should be accepted via special_values (case-insensitive)"


def test_regex_valid_value_still_ok():
    """A value matching the regex should not generate an issue."""
    issues = _issues_for_regex(
        col="creator",
        values=["Dupont, Jean"],
        pattern=r"^[^,]+,\s*.+",
        special_values=["Anonyme"],
    )
    assert issues == []


def test_regex_invalid_value_still_errors():
    """A value that is neither regex-valid nor in special_values should error."""
    issues = _issues_for_regex(
        col="creator",
        values=["pas de virgule ici"],
        pattern=r"^[^,]+,\s*.+",
        special_values=["Anonyme"],
    )
    assert len(issues) == 1


def test_regex_inconnue_for_created():
    """'Inconnue' in nakala:created with W3C-DTF regex should not produce an issue."""
    issues = _issues_for_regex(
        col="nakala:created",
        values=["Inconnue"],
        pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$",
        special_values=["Inconnue"],
    )
    assert issues == [], "'Inconnue' should bypass the W3C-DTF regex check"


def test_regex_inconnue_lowercase():
    """'inconnue' (lowercase) is also accepted via case-insensitive special_values."""
    issues = _issues_for_regex(
        col="nakala:created",
        values=["inconnue"],
        pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$",
        special_values=["Inconnue"],
    )
    assert issues == []


def test_regex_valid_date_still_ok():
    """A valid W3C-DTF date should not raise an issue even with special_values set."""
    issues = _issues_for_regex(
        col="nakala:created",
        values=["2024-01-15"],
        pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$",
        special_values=["Inconnue"],
    )
    assert issues == []


def test_regex_arbitrary_text_still_errors():
    """An arbitrary string that is not in special_values and not regex-valid should error."""
    issues = _issues_for_regex(
        col="nakala:created",
        values=["n'importe quoi"],
        pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$",
        special_values=["Inconnue"],
    )
    assert len(issues) == 1


# ---------------------------------------------------------------------------
# Tests generic.content_type avec special_values
# ---------------------------------------------------------------------------

def test_content_type_special_value_bypasses():
    """'Inconnu' in an integer column should be accepted via special_values."""
    issues = _issues_for_content_type(
        col="annee",
        values=["Inconnu"],
        content_type="integer",
        special_values=["Inconnu"],
    )
    assert issues == [], "'Inconnu' should bypass content_type check"


def test_content_type_special_value_case_insensitive():
    """special_values for content_type is also case-insensitive."""
    issues = _issues_for_content_type(
        col="annee",
        values=["INCONNU"],
        content_type="integer",
        special_values=["Inconnu"],
    )
    assert issues == []


def test_content_type_valid_value_ok():
    """A valid integer should not generate an issue."""
    issues = _issues_for_content_type(
        col="annee",
        values=["2024"],
        content_type="integer",
        special_values=["Inconnu"],
    )
    assert issues == []


def test_content_type_invalid_still_errors():
    """A non-integer, non-special value should still produce an issue."""
    issues = _issues_for_content_type(
        col="annee",
        values=["pas_un_entier"],
        content_type="integer",
        special_values=["Inconnu"],
    )
    assert len(issues) == 1


# ---------------------------------------------------------------------------
# Integration test — nakala_baseline template via TemplateManager
# ---------------------------------------------------------------------------

def test_nakala_template_special_values_integration():
    """When validating with nakala_baseline overlay, 'Inconnue' in nakala:created
    and 'Anonyme' in nakala:creator should produce no issues from their rules."""
    from spreadsheet_qa.core.template_manager import TemplateManager

    mgr = TemplateManager()
    columns = ["nakala:type", "nakala:title", "nakala:creator", "nakala:created", "nakala:license"]
    config = mgr.compile_config(
        generic_id="generic_default",
        overlay_id="nakala_baseline",
        column_names=columns,
    )
    df = pd.DataFrame({
        "nakala:type": pd.array(["http://purl.org/coar/resource_type/c_c513"], dtype="object"),
        "nakala:title": pd.array(["Titre valide"], dtype="object"),
        "nakala:creator": pd.array(["Anonyme"], dtype="object"),
        "nakala:created": pd.array(["Inconnue"], dtype="object"),
        "nakala:license": pd.array(["CC-BY-4.0"], dtype="object"),
    })

    engine = ValidationEngine()
    issues = engine.validate(df, config=config).issues

    # Filter to regex issues on the special-value columns
    regex_issues_creator = [
        i for i in issues
        if i.col == "nakala:creator" and i.rule_id == "generic.regex"
    ]
    regex_issues_created = [
        i for i in issues
        if i.col == "nakala:created" and i.rule_id in ("generic.regex", "nakala.created_format")
    ]

    assert regex_issues_creator == [], (
        f"'Anonyme' should not trigger regex issues on nakala:creator, got: {regex_issues_creator}"
    )
    assert regex_issues_created == [], (
        f"'Inconnue' should not trigger date-format issues on nakala:created, "
        f"got: {regex_issues_created}"
    )
