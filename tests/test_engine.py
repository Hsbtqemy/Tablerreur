"""Tests for ValidationEngine."""

from __future__ import annotations

import pandas as pd
import pytest

from spreadsheet_qa.core.engine import ValidationEngine
from spreadsheet_qa.core.models import Issue


class TestValidationEngine:
    engine = ValidationEngine()

    def test_returns_list_of_issues(self, simple_df):
        issues = self.engine.validate(simple_df, config={})
        assert isinstance(issues, list)
        assert all(isinstance(i, Issue) for i in issues)

    def test_partial_validation_only_targets_columns(self, simple_df):
        all_issues = self.engine.validate(simple_df, config={})
        partial_issues = self.engine.validate(simple_df, columns=["Titre"], config={})
        # Partial should only have issues for "Titre" (per_column rules)
        per_col_partial = [i for i in partial_issues if i.col not in ("__row__", None)]
        assert all(i.col == "Titre" for i in per_col_partial)

    def test_issue_ids_are_deterministic(self, simple_df):
        issues1 = self.engine.validate(simple_df, config={})
        issues2 = self.engine.validate(simple_df, config={})
        ids1 = {i.id for i in issues1}
        ids2 = {i.id for i in issues2}
        assert ids1 == ids2

    def test_hygiene_issues_detected(self, simple_df):
        issues = self.engine.validate(simple_df, columns=["Titre"], config={})
        rule_ids = {i.rule_id for i in issues}
        assert "generic.hygiene.leading_trailing_space" in rule_ids

    def test_pseudo_missing_detected(self, simple_df):
        issues = self.engine.validate(simple_df, columns=["Titre"], config={})
        rule_ids = {i.rule_id for i in issues}
        assert "generic.pseudo_missing" in rule_ids

    def test_disabled_rule_not_run(self, simple_df):
        config = {
            "rules": {
                "generic.hygiene.leading_trailing_space": {"enabled": False}
            }
        }
        issues = self.engine.validate(simple_df, columns=["Titre"], config=config)
        rule_ids = {i.rule_id for i in issues}
        assert "generic.hygiene.leading_trailing_space" not in rule_ids

    def test_empty_dataframe_returns_no_issues(self, empty_df):
        issues = self.engine.validate(empty_df, config={})
        assert issues == []
