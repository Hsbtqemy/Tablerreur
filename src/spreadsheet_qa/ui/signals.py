"""AppSignals: global Qt signal bus.

All inter-component communication goes through these signals so that
modules remain loosely coupled and can be tested in isolation.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from spreadsheet_qa.core.models import DatasetMeta, Issue, Patch


class AppSignals(QObject):
    """Singleton signal hub."""

    # Emitted after a new file is loaded
    dataset_loaded = Signal(object)  # DatasetMeta

    # Emitted after IssueStore is updated (full or partial)
    issues_updated = Signal()

    # Emitted after a patch is applied or undone
    patch_applied = Signal(object)   # Patch
    patch_undone = Signal(object)    # Patch

    # Emitted when the user selects an issue (jump-to-cell)
    issue_selected = Signal(object)  # Issue

    # Request a cell edit (from table view to FixController)
    cell_edit_requested = Signal(int, str, object)  # row, col, new_value

    # Emitted when validation starts/finishes
    validation_started = Signal()
    validation_finished = Signal(int)  # total issue count

    # Project saved
    project_saved = Signal(str)  # folder path

    # Undo/redo stack changed (update toolbar buttons)
    history_changed = Signal(bool, bool)  # can_undo, can_redo

    # Emitted when active template or overlay changes (generic_id, overlay_id or "")
    template_changed = Signal(str, str)

    # Emitted when an issue status is changed by the user (EXCEPTED / IGNORED)
    # Carry (issue_id, new_status_value) so a handler can persist to exceptions.yml
    issue_status_changed = Signal(str, str)

    # Status bar messages
    status_message = Signal(str)


_instance: AppSignals | None = None


def get_signals() -> AppSignals:
    """Return the singleton AppSignals instance."""
    global _instance
    if _instance is None:
        _instance = AppSignals()
    return _instance


def reset_signals() -> None:
    """Reset singleton — for testing only."""
    global _instance
    _instance = None
