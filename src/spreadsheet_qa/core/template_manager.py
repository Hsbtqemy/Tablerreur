"""TemplateManager: discover, load, and compile validation templates.

Handles three template scopes:

- **builtin**: shipped with the package under resources/templates/builtin/
- **user**: per-user config directory (platform-specific)
- **project**: inside the current project folder under templates/

A template is one YAML file. Overlays (type=overlay) are merged on top of a
generic base template. The ``compile_config()`` method returns a dict ready for
``ValidationEngine.validate()``.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_log = logging.getLogger(__name__)

from spreadsheet_qa.core.resources import get_builtin_templates_dir
from spreadsheet_qa.core.template import TemplateLoader


# ---------------------------------------------------------------------------
# TemplateInfo
# ---------------------------------------------------------------------------


@dataclass
class TemplateInfo:
    """Describes one discovered template file."""

    id: str          # e.g. "generic_default" or "nakala_baseline"
    name: str        # Human-readable display name
    scope: str       # "builtin" | "user" | "project"
    type: str        # "generic" | "overlay"
    path: Path
    readonly: bool   # True for builtin templates


# ---------------------------------------------------------------------------
# TemplateManager
# ---------------------------------------------------------------------------


class TemplateManager:
    """Discover templates and compile them into ValidationEngine configs.

    Args:
        project_dir: If provided, also searches ``<project_dir>/templates/``
            for project-scoped templates.
    """

    def __init__(self, project_dir: Path | None = None) -> None:
        self._project_dir = project_dir
        self._loader = TemplateLoader()

    # ------------------------------------------------------------------
    # Template discovery
    # ------------------------------------------------------------------

    def list_templates(
        self, type_filter: str | None = None
    ) -> list[TemplateInfo]:
        """Return all known templates from all scopes.

        Args:
            type_filter: If ``"generic"`` or ``"overlay"``, return only that
                type. ``None`` returns all.
        """
        templates: list[TemplateInfo] = []
        templates.extend(self._discover_builtin())
        templates.extend(self._discover_user())
        if self._project_dir:
            templates.extend(self._discover_project())

        if type_filter:
            templates = [t for t in templates if t.type == type_filter]
        return templates

    def _discover_builtin(self) -> list[TemplateInfo]:
        builtin_dir = get_builtin_templates_dir()
        return self._scan_dir(builtin_dir, scope="builtin", readonly=True)

    def _discover_user(self) -> list[TemplateInfo]:
        user_dir = self.get_user_templates_dir()
        if not user_dir.exists():
            return []
        return self._scan_dir(user_dir, scope="user", readonly=False)

    def _discover_project(self) -> list[TemplateInfo]:
        assert self._project_dir is not None
        proj_dir = self._project_dir / "templates"
        if not proj_dir.exists():
            return []
        return self._scan_dir(proj_dir, scope="project", readonly=False)

    def _scan_dir(
        self, directory: Path, scope: str, readonly: bool
    ) -> list[TemplateInfo]:
        results: list[TemplateInfo] = []
        for yml_path in sorted(directory.glob("*.yml")):
            try:
                data = yaml.safe_load(yml_path.read_text(encoding="utf-8")) or {}
            except Exception as exc:
                _log.warning("Could not parse template %s: %s", yml_path, exc)
                continue

            template_id = data.get("id") or yml_path.stem
            template_name = data.get("name") or template_id
            template_type = data.get("type", "generic")
            results.append(
                TemplateInfo(
                    id=template_id,
                    name=template_name,
                    scope=scope,
                    type=template_type,
                    path=yml_path,
                    readonly=readonly,
                )
            )
        return results

    # ------------------------------------------------------------------
    # User config directory
    # ------------------------------------------------------------------

    def get_user_templates_dir(self) -> Path:
        """Return the per-user templates directory (platform-specific)."""
        import platform

        system = platform.system()
        if system == "Darwin":
            base = Path.home() / "Library" / "Application Support" / "Tablerreur"
        elif system == "Windows":
            appdata = Path(
                __import__("os").environ.get("APPDATA", str(Path.home()))
            )
            base = appdata / "Tablerreur"
        else:
            # Linux / other
            xdg = Path(
                __import__("os").environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
            )
            base = xdg / "Tablerreur"

        return base / "templates"

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    def _resolve_path(self, template_id: str) -> Path | None:
        """Resolve a template ID to a file path across all scopes.

        Priority: project > user > builtin.
        """
        # Project scope (highest priority)
        if self._project_dir:
            p = self._project_dir / "templates" / f"{template_id}.yml"
            if p.exists():
                return p

        # User scope
        p = self.get_user_templates_dir() / f"{template_id}.yml"
        if p.exists():
            return p

        # Builtin scope
        p = get_builtin_templates_dir() / f"{template_id}.yml"
        if p.exists():
            return p

        return None

    # ------------------------------------------------------------------
    # Config compilation
    # ------------------------------------------------------------------

    def compile_config(
        self,
        generic_id: str = "generic_default",
        overlay_id: str | None = None,
        column_names: list[str] | None = None,
        nakala_client: Any = None,
    ) -> dict:
        """Load, merge, and expand a template into a ValidationEngine config.

        Args:
            generic_id: Template ID for the generic base (e.g. ``"generic_default"``).
            overlay_id: Optional overlay template ID (e.g. ``"nakala_baseline"``).
            column_names: Actual column names from the loaded dataset.  Used to
                expand wildcard column patterns.
            nakala_client: If provided, injected into config as ``"_nakala_client"``
                so NAKALA rules can fetch vocabularies.

        Returns:
            A config dict ready for ``ValidationEngine.validate()``.
        """
        # Resolve paths
        base_path = self._resolve_path(generic_id)
        if base_path is None:
            _log.warning("Template '%s' not found; using empty config.", generic_id)
            base_path_arg = None
        else:
            base_path_arg = base_path

        overlay_path: Path | None = None
        if overlay_id:
            overlay_path = self._resolve_path(overlay_id)
            if overlay_path is None:
                _log.warning("Overlay '%s' not found; ignoring.", overlay_id)

        # Load + deep-merge
        config: dict
        if base_path_arg is not None:
            config = self._loader.load(base_path_arg, overlay_path)
        elif overlay_path is not None:
            config = self._loader.load(overlay_path)
        else:
            config = {}

        # Warn about unknown rule IDs
        self._warn_unknown_rules(config)

        # Expand wildcard column patterns against actual column names
        if column_names is not None:
            config = self._loader.expand_wildcards(config, column_names)

        # Inject NAKALA client for vocabulary-based rules
        if nakala_client is not None:
            config["_nakala_client"] = nakala_client

        return config

    def _warn_unknown_rules(self, config: dict) -> None:
        """Emit a warning for any rule IDs in config not in the registry."""
        from spreadsheet_qa.core.rule_base import registry as _registry

        known = set(_registry.all_ids())
        for rule_id in config.get("rules", {}):
            if rule_id not in known:
                _log.warning("Template references unknown rule: %r", rule_id)
