"""Rule base class and RuleRegistry singleton."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from spreadsheet_qa.core.models import Issue


class Rule(ABC):
    """Abstract base for all validation rules."""

    #: Stable unique identifier, e.g. "generic.hygiene.leading_space"
    rule_id: str

    #: Human-readable name shown in the UI
    name: str = ""

    #: Default severity (can be overridden via template config)
    default_severity: str = "WARNING"

    #: Whether this rule checks a single column at a time (True) or the
    #: whole DataFrame (False — used for cross-column/global rules).
    per_column: bool = True

    @abstractmethod
    def check(
        self, df: pd.DataFrame, col: str | None, config: dict[str, Any]
    ) -> list["Issue"]:
        """Run the rule and return a list of Issue objects.

        Args:
            df: The full data DataFrame (string dtype, NaN for empty).
            col: Column name to check. None if per_column=False.
            config: Merged rule config from the template.

        Returns:
            List of Issue objects found. Empty list = no issues.
        """


class RuleRegistry:
    """Singleton registry mapping rule_id → Rule class."""

    _instance: "RuleRegistry | None" = None
    _rules: dict[str, type[Rule]]

    def __new__(cls) -> "RuleRegistry":
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._rules = {}
            cls._instance = inst
        return cls._instance

    def register(self, cls: type[Rule]) -> type[Rule]:
        """Register a Rule class. Can be used as a decorator."""
        self._rules[cls.rule_id] = cls
        return cls

    def get(self, rule_id: str) -> type[Rule] | None:
        return self._rules.get(rule_id)

    def all_ids(self) -> list[str]:
        return sorted(self._rules.keys())

    def all_rules(self) -> list[type[Rule]]:
        return [self._rules[k] for k in self.all_ids()]


# Module-level convenience instance
registry = RuleRegistry()
