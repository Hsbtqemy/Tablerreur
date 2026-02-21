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
from spreadsheet_qa.core.rules.allowed_values import AllowedValuesRule
from spreadsheet_qa.core.rules.case_rule import CaseRule
from spreadsheet_qa.core.rules.forbidden_chars import ForbiddenCharsRule
from spreadsheet_qa.core.rules.length import LengthRule
from spreadsheet_qa.core.rules.list_items import ListItemsRule
from spreadsheet_qa.core.rules.regex_rule import RegexRule
from spreadsheet_qa.core.rules.required import RequiredRule
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

    def test_threshold_090_triggers_on_91pct_numeric(self):
        # 91 integers + 9 non-integers = 91% → above 0.90 threshold → issues
        values = [str(i) for i in range(91)] + ["texte"] * 9
        df = pd.DataFrame({"N": values})
        issues = self.rule.check(df, "N", {"min_count": 20, "threshold": 0.90})
        assert len(issues) == 9

    def test_threshold_095_silent_on_91pct_numeric(self):
        # 91% < 0.95 default threshold → no dominant type inferred → no issues
        values = [str(i) for i in range(91)] + ["texte"] * 9
        df = pd.DataFrame({"N": values})
        issues = self.rule.check(df, "N", {"min_count": 20, "threshold": 0.95})
        assert issues == []


# ---------------------------------------------------------------------------
# Rare values
# ---------------------------------------------------------------------------


class TestRareValuesRule:
    rule = RareValuesRule()

    def test_dormant_when_not_configured(self):
        """Without detect_rare_values=True the rule produces no issues."""
        vals = ["Article"] * 10 + ["Zarticle"]
        df = pd.DataFrame({"Type": vals})
        issues = self.rule.check(df, "Type", {})
        assert issues == []

    def test_detects_rare_value(self):
        """Value appearing once in a column with enough rows is flagged."""
        vals = ["Article"] * 10 + ["Rapport"] * 8 + ["Zarticle"]
        df = pd.DataFrame({"Type": vals})
        issues = self.rule.check(df, "Type", {"detect_rare_values": True})
        assert any(i.original == "Zarticle" for i in issues)
        assert issues[0].severity == Severity.SUSPICION

    def test_message_is_french(self):
        """Issue message uses expected French wording."""
        vals = ["A"] * 10 + ["B"]
        df = pd.DataFrame({"Col": vals})
        issues = self.rule.check(df, "Col", {"detect_rare_values": True})
        assert len(issues) == 1
        assert "n'apparaît que" in issues[0].message
        assert "possible erreur de saisie" in issues[0].message

    def test_no_suggestion(self):
        """No auto-fix suggestion is produced."""
        vals = ["A"] * 10 + ["B"]
        df = pd.DataFrame({"Col": vals})
        issues = self.rule.check(df, "Col", {"detect_rare_values": True})
        assert issues[0].suggestion is None

    def test_case_insensitive_counting(self):
        """'OUI' and 'oui' are counted together and are not rare."""
        # 1×OUI + 9×oui = 10 occurrences → not rare; 'non' ×5 → not rare
        vals = ["OUI"] + ["oui"] * 9 + ["non"] * 5
        df = pd.DataFrame({"Réponse": vals})
        issues = self.rule.check(df, "Réponse", {"detect_rare_values": True})
        assert not any(str(i.original).lower() == "oui" for i in issues)

    def test_skipped_when_total_below_min(self):
        """Rule does not fire when non-empty count < rare_min_total (default 10)."""
        vals = ["A"] * 5 + ["B"]  # total = 6 < 10
        df = pd.DataFrame({"Col": vals})
        issues = self.rule.check(df, "Col", {"detect_rare_values": True})
        assert issues == []

    def test_custom_threshold(self):
        """Values appearing ≤ rare_threshold times are flagged."""
        vals = ["A"] * 10 + ["B"] * 2 + ["C"]
        df = pd.DataFrame({"Col": vals})
        issues = self.rule.check(df, "Col", {"detect_rare_values": True, "rare_threshold": 2})
        originals = {i.original for i in issues}
        assert "B" in originals
        assert "C" in originals

    def test_custom_min_total(self):
        """Custom rare_min_total allows analysis on smaller datasets."""
        vals = ["A"] * 5 + ["B"]  # total = 6
        df = pd.DataFrame({"Col": vals})
        issues = self.rule.check(df, "Col", {"detect_rare_values": True, "rare_min_total": 5})
        assert any(i.original == "B" for i in issues)


# ---------------------------------------------------------------------------
# Allowed values
# ---------------------------------------------------------------------------


class TestAllowedValuesRule:
    rule = AllowedValuesRule()

    def test_flags_value_not_in_list(self):
        df = pd.DataFrame({"Statut": ["A", "B", "D"]})
        issues = self.rule.check(df, "Statut", {"allowed_values": ["A", "B", "C"]})
        assert len(issues) == 1
        assert issues[0].original == "D"
        assert issues[0].severity == Severity.ERROR

    def test_no_issue_for_allowed_value(self):
        df = pd.DataFrame({"Statut": ["A", "B", "C"]})
        issues = self.rule.check(df, "Statut", {"allowed_values": ["A", "B", "C"]})
        assert issues == []

    def test_empty_cell_ignored(self):
        df = pd.DataFrame({"Statut": ["", None]})
        issues = self.rule.check(df, "Statut", {"allowed_values": ["A", "B"]})
        assert issues == []

    def test_no_allowed_values_rule_inactive(self):
        df = pd.DataFrame({"Statut": ["X", "Y", "Z"]})
        issues = self.rule.check(df, "Statut", {})
        assert issues == []

    def test_long_vocab_truncated_in_message(self):
        allowed = [str(i) for i in range(15)]  # 15 items → truncated
        df = pd.DataFrame({"Code": ["99"]})
        issues = self.rule.check(df, "Code", {"allowed_values": allowed})
        assert len(issues) == 1
        assert "…" in issues[0].message

    def test_list_mode_valid_items_no_issue(self):
        df = pd.DataFrame({"Lang": ["fr|en"]})
        cfg = {"allowed_values": ["fr", "en", "de"], "list_separator": "|"}
        issues = self.rule.check(df, "Lang", cfg)
        assert issues == []

    def test_list_mode_invalid_item_flagged(self):
        df = pd.DataFrame({"Lang": ["fr|es"]})
        cfg = {"allowed_values": ["fr", "en", "de"], "list_separator": "|"}
        issues = self.rule.check(df, "Lang", cfg)
        assert len(issues) == 1
        assert "es" in issues[0].message

    def test_single_value_mode_preserved(self):
        """Without list_separator, the whole cell is checked (legacy behaviour)."""
        df = pd.DataFrame({"Lang": ["fr|en"]})
        cfg = {"allowed_values": ["fr", "en"]}
        issues = self.rule.check(df, "Lang", cfg)
        assert len(issues) == 1  # "fr|en" as a whole is not in the list

    def test_allowed_values_locked_does_not_change_rule_behavior(self):
        """allowed_values_locked is a UI-only flag; rule outcome is identical."""
        df = pd.DataFrame({"Statut": ["A", "B", "D"]})
        issues_locked = self.rule.check(
            df, "Statut", {"allowed_values": ["A", "B", "C"], "allowed_values_locked": True}
        )
        issues_unlocked = self.rule.check(
            df, "Statut", {"allowed_values": ["A", "B", "C"], "allowed_values_locked": False}
        )
        assert len(issues_locked) == len(issues_unlocked) == 1


# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------


class TestRegexRule:
    rule = RegexRule()

    def test_valid_value_no_issue(self):
        df = pd.DataFrame({"Date": ["2024-01-15"]})
        issues = self.rule.check(df, "Date", {"regex": r"^\d{4}-\d{2}-\d{2}$"})
        assert issues == []

    def test_invalid_value_flagged(self):
        df = pd.DataFrame({"Date": ["15/01/2024"]})
        issues = self.rule.check(df, "Date", {"regex": r"^\d{4}-\d{2}-\d{2}$"})
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR
        assert "15/01/2024" in issues[0].message

    def test_empty_cell_ignored(self):
        df = pd.DataFrame({"Date": ["", None]})
        issues = self.rule.check(df, "Date", {"regex": r"^\d{4}-\d{2}-\d{2}$"})
        assert issues == []

    def test_no_regex_rule_inactive(self):
        df = pd.DataFrame({"Date": ["anything"]})
        issues = self.rule.check(df, "Date", {})
        assert issues == []

    def test_invalid_regex_no_crash(self):
        df = pd.DataFrame({"Date": ["2024-01-01"]})
        issues = self.rule.check(df, "Date", {"regex": "[unclosed"})
        assert issues == []  # bad regex → silent skip, no crash

    def test_case_insensitive_flag_inline(self):
        """(?i) inline flag is handled natively by re.compile — no regex_rule.py change needed."""
        pattern = r"(?i)^(oui|non|o|n|vrai|faux|true|false|1|0)$"
        df = pd.DataFrame({"Réponse": ["OUI", "Non", "TRUE", "faux", "1"]})
        issues = self.rule.check(df, "Réponse", {"regex": pattern})
        assert issues == []

    def test_case_insensitive_flag_rejects_wrong_value(self):
        pattern = r"(?i)^(oui|non)$"
        df = pd.DataFrame({"Réponse": ["maybe"]})
        issues = self.rule.check(df, "Réponse", {"regex": pattern})
        assert len(issues) == 1


# ---------------------------------------------------------------------------
# Multiline
# ---------------------------------------------------------------------------


class TestLengthRule:
    rule = LengthRule()

    def test_too_short_flagged(self):
        df = pd.DataFrame({"Code": ["AB"]})
        issues = self.rule.check(df, "Code", {"min_length": 3})
        assert len(issues) == 1
        assert issues[0].severity == Severity.WARNING
        assert "trop courte" in issues[0].message

    def test_exact_min_length_ok(self):
        df = pd.DataFrame({"Code": ["ABC"]})
        issues = self.rule.check(df, "Code", {"min_length": 3})
        assert issues == []

    def test_too_long_flagged(self):
        df = pd.DataFrame({"Code": ["ABCDEFGHIJK"]})  # 11 chars
        issues = self.rule.check(df, "Code", {"max_length": 10})
        assert len(issues) == 1
        assert "trop longue" in issues[0].message

    def test_exact_max_length_ok(self):
        df = pd.DataFrame({"Code": ["ABCDEFGHIJ"]})  # 10 chars
        issues = self.rule.check(df, "Code", {"max_length": 10})
        assert issues == []

    def test_both_bounds_respected(self):
        df = pd.DataFrame({"Code": ["A", "ABC", "ABCDEFGHIJK"]})
        issues = self.rule.check(df, "Code", {"min_length": 2, "max_length": 10})
        assert len(issues) == 2
        originals = {i.original for i in issues}
        assert "A" in originals
        assert "ABCDEFGHIJK" in originals

    def test_empty_cell_ignored(self):
        df = pd.DataFrame({"Code": ["", None]})
        issues = self.rule.check(df, "Code", {"min_length": 3})
        assert issues == []

    def test_no_bounds_rule_inactive(self):
        df = pd.DataFrame({"Code": ["X"]})
        issues = self.rule.check(df, "Code", {})
        assert issues == []


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


# ---------------------------------------------------------------------------
# RequiredRule
# ---------------------------------------------------------------------------


class TestRequiredRule:
    rule = RequiredRule()

    def test_empty_cell_flagged(self):
        df = pd.DataFrame({"Col": [""]})
        issues = self.rule.check(df, "Col", {"required": True})
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR

    def test_pseudo_missing_flagged(self):
        df = pd.DataFrame({"Col": ["N/A"]})
        issues = self.rule.check(df, "Col", {"required": True})
        assert len(issues) == 1
        assert "N/A" in issues[0].message

    def test_valid_value_no_issue(self):
        df = pd.DataFrame({"Col": ["données"]})
        issues = self.rule.check(df, "Col", {"required": True})
        assert issues == []

    def test_required_false_no_issue(self):
        df = pd.DataFrame({"Col": [""]})
        issues = self.rule.check(df, "Col", {"required": False})
        assert issues == []

    def test_required_absent_no_issue(self):
        df = pd.DataFrame({"Col": [""]})
        issues = self.rule.check(df, "Col", {})
        assert issues == []

    def test_custom_empty_tokens(self):
        df = pd.DataFrame({"Col": ["X", "N/A"]})
        issues = self.rule.check(df, "Col", {"required": True, "empty_tokens": ["X"]})
        # "X" is in custom tokens → flagged; "N/A" is not → ok
        assert len(issues) == 1
        assert issues[0].original == "X"

    def test_nan_cell_flagged(self):
        df = pd.DataFrame({"Col": [None]})
        issues = self.rule.check(df, "Col", {"required": True})
        assert len(issues) == 1


# ---------------------------------------------------------------------------
# ForbiddenCharsRule
# ---------------------------------------------------------------------------


class TestForbiddenCharsRule:
    rule = ForbiddenCharsRule()

    def test_semicolon_flagged(self):
        df = pd.DataFrame({"Col": ["hello;world"]})
        issues = self.rule.check(df, "Col", {"forbidden_chars": ";"})
        assert len(issues) == 1
        assert issues[0].severity == Severity.WARNING
        assert "point-virgule" in issues[0].message

    def test_tab_flagged_with_readable_name(self):
        df = pd.DataFrame({"Col": ["hello\tworld"]})
        issues = self.rule.check(df, "Col", {"forbidden_chars": "\t"})
        assert len(issues) == 1
        assert "tabulation" in issues[0].message

    def test_multiple_forbidden_chars_both_mentioned(self):
        df = pd.DataFrame({"Col": ["a|b;c"]})
        issues = self.rule.check(df, "Col", {"forbidden_chars": ";|"})
        assert len(issues) == 1
        msg = issues[0].message
        assert "point-virgule" in msg
        assert "barre verticale" in msg

    def test_allowed_char_no_issue(self):
        df = pd.DataFrame({"Col": ["hello world"]})
        issues = self.rule.check(df, "Col", {"forbidden_chars": ";"})
        assert issues == []

    def test_no_config_no_issue(self):
        df = pd.DataFrame({"Col": ["hello;world"]})
        issues = self.rule.check(df, "Col", {})
        assert issues == []

    def test_empty_cell_ignored(self):
        df = pd.DataFrame({"Col": [""]})
        issues = self.rule.check(df, "Col", {"forbidden_chars": ";"})
        assert issues == []


# ---------------------------------------------------------------------------
# CaseRule
# ---------------------------------------------------------------------------


class TestCaseRule:
    rule = CaseRule()

    def test_upper_wrong_case_flagged(self):
        df = pd.DataFrame({"Col": ["hello"]})
        issues = self.rule.check(df, "Col", {"expected_case": "upper"})
        assert len(issues) == 1
        assert issues[0].severity == Severity.WARNING
        assert issues[0].suggestion == "HELLO"
        assert "HELLO" in issues[0].message

    def test_upper_correct_case_no_issue(self):
        df = pd.DataFrame({"Col": ["HELLO"]})
        issues = self.rule.check(df, "Col", {"expected_case": "upper"})
        assert issues == []

    def test_lower_wrong_case_flagged(self):
        df = pd.DataFrame({"Col": ["Hello"]})
        issues = self.rule.check(df, "Col", {"expected_case": "lower"})
        assert len(issues) == 1
        assert issues[0].suggestion == "hello"

    def test_title_wrong_case_flagged(self):
        df = pd.DataFrame({"Col": ["hello world"]})
        issues = self.rule.check(df, "Col", {"expected_case": "title"})
        assert len(issues) == 1
        assert issues[0].suggestion == "Hello World"

    def test_title_correct_case_no_issue(self):
        df = pd.DataFrame({"Col": ["Hello World"]})
        issues = self.rule.check(df, "Col", {"expected_case": "title"})
        assert issues == []

    def test_empty_cell_ignored(self):
        df = pd.DataFrame({"Col": [""]})
        issues = self.rule.check(df, "Col", {"expected_case": "upper"})
        assert issues == []

    def test_digits_only_ignored(self):
        df = pd.DataFrame({"Col": ["123"]})
        issues = self.rule.check(df, "Col", {"expected_case": "upper"})
        assert issues == []

    def test_no_config_no_issue(self):
        df = pd.DataFrame({"Col": ["hello"]})
        issues = self.rule.check(df, "Col", {})
        assert issues == []


# ---------------------------------------------------------------------------
# ListItemsRule
# ---------------------------------------------------------------------------


class TestListItemsRule:
    rule = ListItemsRule()
    sep = {"list_separator": "|"}

    def test_valid_list_no_issue(self):
        df = pd.DataFrame({"Lang": ["fr|en|de"]})
        issues = self.rule.check(df, "Lang", self.sep)
        assert issues == []

    def test_empty_item_flagged(self):
        df = pd.DataFrame({"Lang": ["fr||en"]})
        issues = self.rule.check(df, "Lang", self.sep)
        assert len(issues) == 1
        assert "vide" in issues[0].message

    def test_min_items_violation(self):
        df = pd.DataFrame({"Lang": ["fr"]})
        issues = self.rule.check(df, "Lang", {**self.sep, "list_min_items": 2})
        assert len(issues) == 1
        assert "Trop peu" in issues[0].message

    def test_max_items_violation(self):
        df = pd.DataFrame({"Lang": ["a|b|c|d"]})
        issues = self.rule.check(df, "Lang", {**self.sep, "list_max_items": 3})
        assert len(issues) == 1
        assert "Trop d'éléments" in issues[0].message

    def test_unique_violation(self):
        df = pd.DataFrame({"Lang": ["fr|en|fr"]})
        issues = self.rule.check(df, "Lang", {**self.sep, "list_unique": True})
        assert len(issues) == 1
        assert "double" in issues[0].message
        assert "fr" in issues[0].message

    def test_trim_removes_spaces(self):
        df = pd.DataFrame({"Lang": [" fr | en "]})
        issues = self.rule.check(df, "Lang", {**self.sep, "list_trim": True})
        assert issues == []

    def test_no_separator_dormant(self):
        df = pd.DataFrame({"Lang": ["fr|en"]})
        issues = self.rule.check(df, "Lang", {})
        assert issues == []

    def test_empty_cell_ignored(self):
        df = pd.DataFrame({"Lang": [""]})
        issues = self.rule.check(df, "Lang", self.sep)
        assert issues == []

    def test_severity_is_warning(self):
        df = pd.DataFrame({"Lang": ["fr||en"]})
        issues = self.rule.check(df, "Lang", self.sep)
        assert issues[0].severity == Severity.WARNING
