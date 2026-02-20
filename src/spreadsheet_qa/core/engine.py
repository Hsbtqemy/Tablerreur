"""ValidationEngine: orchestrates running rules against a DataFrame.

The engine is stateless — it does not own an IssueStore.
Callers are responsible for feeding the results into an IssueStore.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

import pandas as pd

_log = logging.getLogger(__name__)

# Import rules module to trigger all @registry.register decorators
import spreadsheet_qa.core.rules  # noqa: F401
from spreadsheet_qa.core.models import Issue
from spreadsheet_qa.core.rule_base import Rule, RuleRegistry, registry


class ValidationEngine:
    """Run validation rules and return Issue objects.

    Usage::

        engine = ValidationEngine()
        issues = engine.validate(df, columns=None, config=rule_config)
    """

    def __init__(self, rule_registry: RuleRegistry | None = None) -> None:
        self._registry = rule_registry or registry

    def validate(
        self,
        df: pd.DataFrame,
        columns: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> list[Issue]:
        """Run all registered rules and return all found issues.

        Args:
            df: The data DataFrame (string dtype, int-indexed).
            columns: If provided, only run per_column rules for these columns.
                     Global (per_column=False) rules always run on the full df.
            config: Template config dict.  Structure::

                {
                    "rules": {
                        "generic.hygiene.leading_trailing_space": {
                            "enabled": True,
                            "severity": "WARNING",
                        },
                        ...
                    },
                    "columns": {
                        "Titre": {
                            "unique": False,
                            "multiline_ok": False,
                            ...
                        }
                    }
                }

        Returns:
            Flat list of Issue objects.
        """
        if config is None:
            config = {}

        rules_config: dict[str, dict] = config.get("rules", {})
        columns_config: dict[str, dict] = config.get("columns", {})

        # Determine which columns to validate
        target_cols = columns if columns is not None else list(df.columns)

        all_issues: list[Issue] = []

        for rule_cls in self._registry.all_rules():
            rule_inst = rule_cls()
            rule_cfg = {**rules_config.get(rule_inst.rule_id, {})}
            enabled = rule_cfg.pop("enabled", True)
            if not enabled:
                continue

            if rule_inst.per_column:
                for col in target_cols:
                    col_cfg = columns_config.get(col, {})
                    # Extract per-rule overrides separately so the raw
                    # `rule_overrides` dict never lands in merged_cfg.
                    rule_level_override = col_cfg.get("rule_overrides", {}).get(
                        rule_inst.rule_id, {}
                    )
                    col_meta = {k: v for k, v in col_cfg.items() if k != "rule_overrides"}
                    merged_cfg = {**rule_cfg, **col_meta, **rule_level_override}
                    # A rule_override may disable a specific rule for this column.
                    if not merged_cfg.pop("enabled", True):
                        continue
                    try:
                        issues = rule_inst.check(df, col, merged_cfg)
                    except Exception as exc:
                        # Never crash the whole validation because one rule fails
                        _log.exception(
                            "Rule %s failed on column %r: %s", rule_inst.rule_id, col, exc
                        )
                        issues = []
                    all_issues.extend(issues)
            else:
                # Global rule: only run once per full validation
                if columns is not None:
                    # During partial re-validation skip global rules to avoid
                    # replacing issues from unchanged columns.
                    continue
                try:
                    issues = rule_inst.check(df, None, rule_cfg)
                except Exception as exc:
                    _log.exception("Global rule %s failed: %s", rule_inst.rule_id, exc)
                    issues = []
                all_issues.extend(issues)

        return all_issues
