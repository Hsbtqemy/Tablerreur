"""Tests for individual validation rules."""

from __future__ import annotations

import pandas as pd
import pytest

from spreadsheet_qa.core.models import IssueStatus, Severity
from spreadsheet_qa.core.rules.duplicates import DuplicateRowsRule, UniqueColumnRule
from spreadsheet_qa.core.rules.hygiene import (
    InvisibleCharsRule,
    LeadingTrailingSpaceRule,
    MultipleSpacesRule,
    UnicodeNormalizationRule,
)
from spreadsheet_qa.core.rules.multiline import UnexpectedMultilineRule
from spreadsheet_qa.core.rules.pseudo_missing import PseudoMissingRule
from spreadsheet_qa.core.rules.soft_typing import SoftTypingRule
from spreadsheet_qa.core.rules.rare_values import RareValuesRule


# ---------------------------------------------------------------------------
# Hygiene rules
# ---------------------------------------------------------------------------


class TestLeadingTrailingSpaceRule:
    rule = LeadingTrailingSpaceRule()

    def test_detects_trailing_space(self):
        df = pd.DataFrame({"A": ["hello "]})
        issues = self.rule.check(df, "A", {})
        assert len(issues) == 1
        assert issues[0].suggestion == "hello"
        assert issues[0].severity == Severity.WARNING

    def test_detects_leading_space(self):
        df = pd.DataFrame({"A": [" world"]})
        issues = self.rule.check(df, "A", {})
        assert len(issues) == 1
        assert issues[0].suggestion == "world"

    def test_no_issue_on_clean_value(self):
        df = pd.DataFrame({"A": ["clean"]})
        issues = self.rule.check(df, "A", {})
        assert issues == []

    def test_nan_is_skipped(self):
        df = pd.DataFrame({"A": [float("nan")]})
        issues = self.rule.check(df, "A", {})
        assert issues == []

    def test_issue_id_is_deterministic(self):
        df = pd.DataFrame({"A": ["hello "]})
        i1 = self.rule.check(df, "A", {})[0]
        i2 = self.rule.check(df, "A", {})[0]
        assert i1.id == i2.id


class TestMultipleSpacesRule:
    rule = MultipleSpacesRule()

    def test_detects_double_space(self):
        df = pd.DataFrame({"A": ["hello  world"]})
        issues = self.rule.check(df, "A", {})
        assert len(issues) == 1
        assert issues[0].suggestion == "hello world"

    def test_no_issue_on_single_space(self):
        df = pd.DataFrame({"A": ["hello world"]})
        issues = self.rule.check(df, "A", {})
        assert issues == []


class TestUnicodeNormalizationRule:
    rule = UnicodeNormalizationRule()

    def test_detects_curly_quote(self):
        df = pd.DataFrame({"A": ["\u201ctest\u201d"]})
        issues = self.rule.check(df, "A", {})
        assert len(issues) == 1
        assert '"test"' in issues[0].suggestion

    def test_detects_em_dash(self):
        df = pd.DataFrame({"A": ["before\u2014after"]})
        issues = self.rule.check(df, "A", {})
        assert len(issues) == 1


class TestInvisibleCharsRule:
    rule = InvisibleCharsRule()

    def test_detects_zero_width_space(self):
        df = pd.DataFrame({"A": ["hello\u200bworld"]})
        issues = self.rule.check(df, "A", {})
        assert len(issues) == 1
        assert issues[0].suggestion == "helloworld"


# ---------------------------------------------------------------------------
# Pseudo-missing
# ---------------------------------------------------------------------------


class TestPseudoMissingRule:
    rule = PseudoMissingRule()

    @pytest.mark.parametrize("token", ["NA", "N/A", "NULL", "-", "?", "null", "n/a"])
    def test_detects_default_tokens(self, token):
        df = pd.DataFrame({"A": [token]})
        issues = self.rule.check(df, "A", {})
        assert len(issues) == 1

    def test_no_issue_on_regular_value(self):
        df = pd.DataFrame({"A": ["normal text"]})
        issues = self.rule.check(df, "A", {})
        assert issues == []

    def test_custom_tokens(self):
        df = pd.DataFrame({"A": ["MISSING"]})
        issues = self.rule.check(df, "A", {"tokens": ["MISSING"]})
        assert len(issues) == 1


# ---------------------------------------------------------------------------
# Duplicates
# ---------------------------------------------------------------------------


class TestDuplicateRowsRule:
    rule = DuplicateRowsRule()

    def test_detects_duplicate_rows(self, dup_rows_df):
        issues = self.rule.check(dup_rows_df, None, {})
        assert len(issues) == 1
        assert issues[0].row == 1  # second occurrence flagged

    def test_no_duplicates(self):
        df = pd.DataFrame({"A": ["x", "y", "z"]})
        issues = self.rule.check(df, None, {})
        assert issues == []


class TestUniqueColumnRule:
    rule = UniqueColumnRule()

    def test_detects_duplicate_in_unique_col(self):
        df = pd.DataFrame({"ID": ["a", "b", "a"]})
        issues = self.rule.check(df, "ID", {"unique": True})
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR

    def test_no_error_if_unique_not_set(self):
        df = pd.DataFrame({"ID": ["a", "b", "a"]})
        issues = self.rule.check(df, "ID", {})  # unique not set → skip
        assert issues == []


# ---------------------------------------------------------------------------
# Soft typing
# ---------------------------------------------------------------------------


class TestSoftTypingRule:
    rule = SoftTypingRule()

    def test_detects_outlier_in_date_column(self):
        dates = [f"2020-{m:02d}-01" for m in range(1, 13)]
        dates = dates * 3  # 36 dates
        df = pd.DataFrame({"Date": dates + ["not-a-date"]})
        issues = self.rule.check(df, "Date", {"min_count": 30})
        assert any(i.original == "not-a-date" for i in issues)

    def test_no_issue_below_min_count(self):
        df = pd.DataFrame({"Date": ["2020-01-01", "bad"]})
        issues = self.rule.check(df, "Date", {"min_count": 30})
        assert issues == []


# ---------------------------------------------------------------------------
# Rare values
# ---------------------------------------------------------------------------


class TestRareValuesRule:
    rule = RareValuesRule()

    def test_detects_hapax(self):
        # 5 values: 4 repeated, 1 hapax
        vals = ["Article"] * 10 + ["Rapport"] * 8 + ["Thèse"] * 7 + ["Chapitre"] * 6 + ["Zarticle"]
        df = pd.DataFrame({"Type": vals})
        issues = self.rule.check(df, "Type", {})
        assert any(i.original == "Zarticle" for i in issues)

    def test_no_issue_when_too_many_distinct(self):
        # 100 distinct → not categorical
        df = pd.DataFrame({"ID": [str(i) for i in range(200)]})
        issues = self.rule.check(df, "ID", {"max_distinct": 50})
        assert issues == []


# ---------------------------------------------------------------------------
# Multiline
# ---------------------------------------------------------------------------


class TestUnexpectedMultilineRule:
    rule = UnexpectedMultilineRule()

    def test_detects_newline(self):
        df = pd.DataFrame({"A": ["line1\nline2"]})
        issues = self.rule.check(df, "A", {})
        assert len(issues) == 1

    def test_no_issue_when_multiline_ok(self):
        df = pd.DataFrame({"A": ["line1\nline2"]})
        issues = self.rule.check(df, "A", {"multiline_ok": True})
        assert issues == []

    def test_suggestion_removes_newline(self):
        df = pd.DataFrame({"A": ["before\nafter"]})
        issues = self.rule.check(df, "A", {})
        assert "\n" not in issues[0].suggestion
