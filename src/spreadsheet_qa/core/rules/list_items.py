"""Per-column multi-value list validation rule.

Validates each individual item in cells that contain multiple values separated
by a declared character (e.g. ``|``, ``;``).  The rule is dormant if
``list_separator`` is not configured for the column.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry


@registry.register
class ListItemsRule(Rule):
    """Validate individual items inside multi-value cells."""

    rule_id = "generic.list_items"
    name = "Éléments de liste"
    default_severity = "WARNING"
    per_column = True

    def check(self, df: pd.DataFrame, col: str | None, config: dict[str, Any]) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        sep: str | None = config.get("list_separator", None)
        if not sep:
            return []

        do_trim: bool = config.get("list_trim", True)
        min_items: int | None = config.get("list_min_items", None)
        max_items: int | None = config.get("list_max_items", None)
        check_unique: bool = config.get("list_unique", False)
        no_empty: bool = config.get("list_no_empty", True)

        if min_items is not None:
            min_items = int(min_items)
        if max_items is not None:
            max_items = int(max_items)

        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []

        for row_idx, val in df[col].items():
            if pd.isna(val):
                continue
            cell = str(val)
            if cell.strip() == "":
                continue

            items = cell.split(sep)
            if do_trim:
                items = [item.strip() for item in items]

            row = int(row_idx)

            # Empty item check
            if no_empty and any(item == "" for item in items):
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=row,
                        col=col,
                        original=val,
                        message=(
                            f"Élément vide détecté dans la liste "
                            f"(vérifiez les séparateurs « {sep} » consécutifs)."
                        ),
                    )
                )
                continue  # skip further checks on this cell — structure is invalid

            n = len(items)

            # Min items
            if min_items is not None and n < min_items:
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=row,
                        col=col,
                        original=val,
                        message=f"Trop peu d'éléments ({n}/{min_items} minimum).",
                    )
                )

            # Max items
            if max_items is not None and n > max_items:
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=row,
                        col=col,
                        original=val,
                        message=f"Trop d'éléments ({n}/{max_items} maximum).",
                    )
                )

            # Unique items
            if check_unique:
                counts = Counter(items)
                dupes = [item for item, cnt in counts.items() if cnt > 1]
                if dupes:
                    dupes_str = ", ".join(f"«{d}»" for d in sorted(dupes))
                    issues.append(
                        Issue.create(
                            rule_id=self.rule_id,
                            severity=severity,
                            row=row,
                            col=col,
                            original=val,
                            message=f"Élément(s) en double dans la liste : {dupes_str}.",
                        )
                    )

        return issues
