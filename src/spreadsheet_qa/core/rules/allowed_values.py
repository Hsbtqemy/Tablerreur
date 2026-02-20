"""Allowed values (controlled vocabulary) rule.

Flags cells whose value is not in the declared allowed_values list for
the column.  The rule is dormant if no allowed_values are configured.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry

_DISPLAY_LIMIT = 10


@registry.register
class AllowedValuesRule(Rule):
    """Flag values not in the declared controlled vocabulary for a column."""

    rule_id = "generic.allowed_values"
    name = "Valeur hors vocabulaire autorisé"
    default_severity = "ERROR"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        allowed: list[str] = config.get("allowed_values", [])
        if not allowed:
            return []

        allowed_set = set(allowed)
        severity = Severity(config.get("severity", self.default_severity))

        # Build display string for the message, truncated if long
        if len(allowed) > _DISPLAY_LIMIT:
            display = ", ".join(f"«{v}»" for v in allowed[:_DISPLAY_LIMIT]) + "…"
        else:
            display = ", ".join(f"«{v}»" for v in allowed)

        sep: str | None = config.get("list_separator", None)
        do_trim: bool = config.get("list_trim", True)

        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if pd.isna(val):
                continue
            cell = str(val)
            if cell.strip() == "":
                continue

            if sep:
                # List mode: check each item individually
                items = cell.split(sep)
                if do_trim:
                    items = [item.strip() for item in items]
                for item in items:
                    if item and item not in allowed_set:
                        issues.append(
                            Issue.create(
                                rule_id=self.rule_id,
                                severity=severity,
                                row=int(row_idx),
                                col=col,
                                original=val,
                                message=(
                                    f"Élément « {item} » non autorisé dans la liste. "
                                    f"Valeurs acceptées : {display}"
                                ),
                                suggestion=None,
                            )
                        )
            else:
                # Single-value mode (original behaviour)
                if cell not in allowed_set:
                    issues.append(
                        Issue.create(
                            rule_id=self.rule_id,
                            severity=severity,
                            row=int(row_idx),
                            col=col,
                            original=val,
                            message=(
                                f"Valeur « {cell} » non autorisée dans « {col} ». "
                                f"Valeurs acceptées : {display}"
                            ),
                            suggestion=None,
                        )
                    )
        return issues
