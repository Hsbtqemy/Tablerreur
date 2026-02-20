"""Tests for template loading, TemplateManager, and rule_overrides in engine."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest
import yaml

from spreadsheet_qa.core.template import TemplateLoader, deep_merge
from spreadsheet_qa.core.template_manager import TemplateInfo, TemplateManager
from spreadsheet_qa.core.engine import ValidationEngine
from spreadsheet_qa.core.resources import get_builtin_templates_dir, get_builtin_template_path


# ---------------------------------------------------------------------------
# 1. Load a built-in generic template
# ---------------------------------------------------------------------------


class TestLoadGenericBuiltin:
    def test_generic_default_loads(self):
        path = get_builtin_template_path("generic_default")
        assert path.exists(), f"generic_default.yml not found at {path}"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert "rules" in data
        assert "columns" in data
        assert len(data["rules"]) >= 5

    def test_generic_strict_loads(self):
        path = get_builtin_template_path("generic_strict")
        assert path.exists()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["id"] == "generic_strict"
        assert data["type"] == "generic"

    def test_nakala_baseline_loads(self):
        path = get_builtin_template_path("nakala_baseline")
        assert path.exists()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["type"] == "overlay"
        assert "required_columns" in data
        assert "nakala:type" in data["required_columns"]

    def test_nakala_extended_loads(self):
        path = get_builtin_template_path("nakala_extended")
        assert path.exists()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["type"] == "overlay"
        assert "recommended_columns" in data


# ---------------------------------------------------------------------------
# 2. Overlay merge
# ---------------------------------------------------------------------------


class TestOverlayMerge:
    def test_deep_merge_scalars(self):
        base = {"a": 1, "b": 2}
        overlay = {"b": 99, "c": 3}
        result = deep_merge(base, overlay)
        assert result == {"a": 1, "b": 99, "c": 3}

    def test_deep_merge_nested(self):
        base = {"rules": {"r1": {"enabled": True, "severity": "WARNING"}}}
        overlay = {"rules": {"r1": {"severity": "ERROR"}, "r2": {"enabled": True}}}
        result = deep_merge(base, overlay)
        assert result["rules"]["r1"]["enabled"] is True   # kept from base
        assert result["rules"]["r1"]["severity"] == "ERROR"  # overridden
        assert "r2" in result["rules"]

    def test_loader_merges_nakala_overlay(self, tmp_path):
        base_path = get_builtin_template_path("generic_default")
        overlay_path = get_builtin_template_path("nakala_baseline")
        loader = TemplateLoader()
        config = loader.load(base_path, overlay_path)
        # Overlay rules should be present
        assert "nakala.deposit_type" in config.get("rules", {})
        # Base rules should be preserved
        assert "generic.hygiene.leading_trailing_space" in config["rules"]
        # required_columns from overlay
        assert "required_columns" in config
        assert "nakala:type" in config["required_columns"]


# ---------------------------------------------------------------------------
# 3. Wildcard expansion
# ---------------------------------------------------------------------------


class TestWildcardExpansion:
    def test_wildcard_applied_to_all_columns(self):
        loader = TemplateLoader()
        config = {
            "columns": {"*": {"kind": "free_text_short", "required": False}},
            "column_groups": {},
        }
        result = loader.expand_wildcards(config, ["A", "B", "C"])
        for col in ["A", "B", "C"]:
            assert col in result["columns"]
            assert result["columns"][col]["kind"] == "free_text_short"

    def test_column_group_pattern_applied(self):
        loader = TemplateLoader()
        config = {
            "columns": {"*": {"kind": "free_text_short"}},
            "column_groups": {"id_*": {"unique": True, "kind": "structured"}},
        }
        result = loader.expand_wildcards(config, ["id_source", "title"])
        assert result["columns"]["id_source"]["unique"] is True
        assert result["columns"]["id_source"]["kind"] == "structured"
        # Non-matching column should keep wildcard default
        assert result["columns"]["title"].get("unique", False) is False

    def test_exact_column_override_wins(self):
        loader = TemplateLoader()
        config = {
            "columns": {
                "*": {"kind": "free_text_short"},
                "Title": {"kind": "free_text_long", "required": True},
            },
            "column_groups": {},
        }
        result = loader.expand_wildcards(config, ["Title", "Other"])
        assert result["columns"]["Title"]["kind"] == "free_text_long"
        assert result["columns"]["Title"]["required"] is True
        assert result["columns"]["Other"]["kind"] == "free_text_short"


# ---------------------------------------------------------------------------
# 4. rule_overrides merge in engine
# ---------------------------------------------------------------------------


class TestRuleOverridesMergeInEngine:
    def test_rule_override_disables_rule_for_column(self):
        """Disabling pseudo_missing for one column should produce no issues for it."""
        df = pd.DataFrame({
            "ColA": ["N/A", "hello", "N/A"],
            "ColB": ["N/A", "world", "N/A"],
        })
        config = {
            "rules": {
                "generic.pseudo_missing": {"enabled": True, "severity": "WARNING"}
            },
            "columns": {
                "ColA": {
                    "rule_overrides": {
                        "generic.pseudo_missing": {"enabled": False}
                    }
                }
            },
        }
        engine = ValidationEngine()
        issues = engine.validate(df, config=config)
        colA_pseudo = [i for i in issues if i.col == "ColA" and i.rule_id == "generic.pseudo_missing"]
        colB_pseudo = [i for i in issues if i.col == "ColB" and i.rule_id == "generic.pseudo_missing"]
        assert len(colA_pseudo) == 0, "ColA pseudo_missing should be disabled by rule_override"
        assert len(colB_pseudo) > 0, "ColB pseudo_missing should still fire"

    def test_rule_override_changes_severity(self):
        """A rule_override can escalate severity for a specific column."""
        df = pd.DataFrame({"Special": ["N/A", "good"]})
        config = {
            "rules": {
                "generic.pseudo_missing": {"enabled": True, "severity": "WARNING"}
            },
            "columns": {
                "Special": {
                    "rule_overrides": {
                        "generic.pseudo_missing": {"severity": "ERROR"}
                    }
                }
            },
        }
        engine = ValidationEngine()
        issues = engine.validate(df, config=config)
        pseudo_issues = [i for i in issues if i.col == "Special" and i.rule_id == "generic.pseudo_missing"]
        assert len(pseudo_issues) == 1
        from spreadsheet_qa.core.models import Severity
        assert pseudo_issues[0].severity == Severity.ERROR


# ---------------------------------------------------------------------------
# 5. TemplateManager.list_templates()
# ---------------------------------------------------------------------------


class TestTemplateManagerListTemplates:
    def test_list_returns_builtin_templates(self):
        mgr = TemplateManager()
        templates = mgr.list_templates()
        ids = [t.id for t in templates]
        assert "generic_default" in ids
        assert "generic_strict" in ids
        assert "nakala_baseline" in ids
        assert "nakala_extended" in ids

    def test_list_filter_by_type(self):
        mgr = TemplateManager()
        generics = mgr.list_templates(type_filter="generic")
        overlays = mgr.list_templates(type_filter="overlay")
        assert all(t.type == "generic" for t in generics)
        assert all(t.type == "overlay" for t in overlays)
        assert len(generics) >= 2
        assert len(overlays) >= 2

    def test_builtin_templates_are_readonly(self):
        mgr = TemplateManager()
        templates = mgr.list_templates()
        builtin = [t for t in templates if t.scope == "builtin"]
        assert all(t.readonly for t in builtin)


# ---------------------------------------------------------------------------
# 6. TemplateManager.compile_config()
# ---------------------------------------------------------------------------


class TestCompileConfig:
    def test_compile_config_returns_rules_and_columns(self):
        mgr = TemplateManager()
        config = mgr.compile_config(
            generic_id="generic_default",
            overlay_id=None,
            column_names=["A", "B"],
        )
        assert "rules" in config
        assert "columns" in config
        assert "A" in config["columns"]
        assert "B" in config["columns"]

    def test_compile_config_with_overlay(self):
        mgr = TemplateManager()
        config = mgr.compile_config(
            generic_id="generic_default",
            overlay_id="nakala_baseline",
            column_names=["nakala:type", "nakala:title"],
        )
        assert "nakala.deposit_type" in config.get("rules", {})
        assert "nakala:type" in config.get("columns", {})

    def test_compile_config_injects_nakala_client(self):
        mgr = TemplateManager()
        mock_client = MagicMock()
        config = mgr.compile_config(
            generic_id="generic_default",
            column_names=["A"],
            nakala_client=mock_client,
        )
        assert config.get("_nakala_client") is mock_client

    def test_compile_config_unknown_template_falls_back(self, caplog):
        import logging
        mgr = TemplateManager()
        with caplog.at_level(logging.WARNING):
            config = mgr.compile_config(
                generic_id="__nonexistent_template__",
                column_names=["A"],
            )
        # Should not crash; fallback to empty config, warning logged
        assert isinstance(config, dict)
        assert any("not found" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# 7. Unknown rule warning
# ---------------------------------------------------------------------------


class TestUnknownRuleWarning:
    def test_unknown_rule_logs_warning(self, caplog):
        import logging
        mgr = TemplateManager()
        config = {"rules": {"__fake.rule.id__": {"enabled": True}}}
        with caplog.at_level(logging.WARNING):
            mgr._warn_unknown_rules(config)
        assert any("__fake.rule.id__" in r.message for r in caplog.records)
