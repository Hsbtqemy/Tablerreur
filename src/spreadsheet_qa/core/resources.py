"""importlib.resources helpers for accessing built-in template files.

Works both in development (editable install) and in a packaged wheel.
"""

from __future__ import annotations

from pathlib import Path


def _builtin_templates_dir() -> Path:
    """Return the Path to resources/templates/builtin/ inside the package."""
    # importlib.resources.files() works for Python 3.9+ and is the modern API.
    # It returns a Traversable that can be resolved to a real Path via __fspath__.
    import importlib.resources as _ir

    ref = _ir.files("spreadsheet_qa.resources.templates.builtin")
    # Convert to a real filesystem Path.  For editable installs this is a
    # plain directory; for wheels it may be a zipimport path — but hatchling
    # ships templates as data files so it is always a real directory.
    return Path(str(ref))


def get_builtin_templates_dir() -> Path:
    """Return the absolute Path to the builtin templates directory."""
    return _builtin_templates_dir()


def get_builtin_template_path(name: str) -> Path:
    """Return the absolute Path to a named built-in template YAML.

    Args:
        name: Template stem name (e.g. ``"generic_default"``).

    Returns:
        Path ending in ``<name>.yml``.
    """
    return _builtin_templates_dir() / f"{name}.yml"
