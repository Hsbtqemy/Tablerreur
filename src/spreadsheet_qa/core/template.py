"""TemplateLoader: load and deep-merge YAML rule templates."""

from __future__ import annotations

import fnmatch
from copy import deepcopy
from pathlib import Path

import yaml


def deep_merge(base: dict, overlay: dict) -> dict:
    """Merge overlay into base. Overlay wins on scalar conflicts.

    Dicts are merged recursively. Lists are replaced (not concatenated).
    """
    result = deepcopy(base)
    for key, val in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = deepcopy(val)
    return result


class TemplateLoader:
    """Load base template + optional overlay and resolve column wildcards."""

    def load(
        self,
        base_path: Path,
        overlay_path: Path | None = None,
    ) -> dict:
        """Return the merged template config dict."""
        config: dict = {}
        if base_path.exists():
            config = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}

        if overlay_path and overlay_path.exists():
            overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8")) or {}
            config = deep_merge(config, overlay)

        return config

    def expand_wildcards(self, config: dict, column_names: list[str]) -> dict:
        """Resolve column_groups glob patterns against actual column names.

        Returns a *new* config dict (deep-copied); the input is not modified.
        The wildcard key '*' in ``config["columns"]`` applies to ALL columns as
        a baseline; column_groups patterns (glob) are layered on top, then exact
        column entries take highest priority.
        """
        columns_cfg: dict = config.get("columns", {})
        column_groups: dict = config.get("column_groups", {})

        # Start with wildcard defaults if present
        wildcard_defaults = columns_cfg.get("*", {})

        resolved: dict = {}
        for col in column_names:
            # Base: wildcard defaults
            resolved[col] = deepcopy(wildcard_defaults)

            # Apply column_groups patterns (glob)
            for pattern, group_cfg in column_groups.items():
                if fnmatch.fnmatch(col, pattern):
                    resolved[col] = deep_merge(resolved[col], group_cfg)

            # Apply exact column overrides (highest priority)
            if col in columns_cfg and col != "*":
                resolved[col] = deep_merge(resolved[col], columns_cfg[col])

        config = deepcopy(config)
        config["columns"] = resolved
        return config
