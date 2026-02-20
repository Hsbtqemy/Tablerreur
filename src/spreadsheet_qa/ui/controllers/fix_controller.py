"""FixController: wraps cell edits in Commands and manages undo/redo."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Slot

from spreadsheet_qa.core.commands import ApplyCellFixCommand, BulkCellFixCommand
from spreadsheet_qa.core.history import CommandHistory
from spreadsheet_qa.core.patch import NullPatchWriter, PatchWriter

if TYPE_CHECKING:
    from spreadsheet_qa.core.issue_store import IssueStore
    from spreadsheet_qa.core.project import NullProjectManager, ProjectManager
    from spreadsheet_qa.ui.controllers.validation_controller import ValidationController
    from spreadsheet_qa.ui.signals import AppSignals
    from spreadsheet_qa.ui.table.table_model import SpreadsheetTableModel


class FixController:
    """Mediates between UI fix actions and the Command/History system."""

    def __init__(
        self,
        table_model: "SpreadsheetTableModel",
        issue_store: "IssueStore",
        signals: "AppSignals",
        validation_controller: "ValidationController",
        patch_writer: PatchWriter | None = None,
        project_manager=None,
    ) -> None:
        self._table_model = table_model
        self._issue_store = issue_store
        self._signals = signals
        self._validation = validation_controller
        self._patch_writer = patch_writer or NullPatchWriter()
        self._project = project_manager
        self._history = CommandHistory()

        self._signals.cell_edit_requested.connect(self._on_cell_edit)

    def set_patch_writer(self, pw: PatchWriter) -> None:
        self._patch_writer = pw

    def set_project_manager(self, pm) -> None:
        self._project = pm

    def apply_fix(
        self,
        row: int,
        col: str,
        new_value: Any,
        issue_id: str | None = None,
    ) -> None:
        """Apply a single-cell fix via a Command."""
        df = self._table_model.df
        old_value = df.at[row, col]

        cmd = ApplyCellFixCommand(
            df=df,
            row=row,
            col=col,
            old_value=old_value,
            new_value=new_value,
            issue_store=self._issue_store,
            patch_writer=self._patch_writer,
            project_manager=self._project,
            issue_id=issue_id,
        )
        self._history.push(cmd)

        # Refresh UI
        col_idx = list(df.columns).index(col)
        self._table_model.refresh_cell(row, col_idx)

        # Emit patch_applied for IssuesPanel refresh
        if cmd.patch:
            self._signals.patch_applied.emit(cmd.patch)

        # Partial re-validation
        self._validation.run_partial([col])
        self._signals.history_changed.emit(self._history.can_undo, self._history.can_redo)

    def apply_bulk(self, matches: list[tuple[int, str, Any, Any]]) -> None:
        """Apply multiple fixes as a single undoable bulk command."""
        df = self._table_model.df
        sub_commands = []
        affected_cols = set()

        for row, col, old_val, new_val in matches:
            cmd = ApplyCellFixCommand(
                df=df,
                row=row,
                col=col,
                old_value=old_val,
                new_value=new_val,
                issue_store=self._issue_store,
                patch_writer=self._patch_writer,
                project_manager=self._project,
            )
            sub_commands.append(cmd)
            affected_cols.add(col)

        if not sub_commands:
            return

        bulk = BulkCellFixCommand(sub_commands, label=f"Bulk fix ({len(sub_commands)} cells)")
        self._history.push(bulk)
        self._table_model.refresh_all()
        self._validation.run_partial(list(affected_cols))
        self._signals.history_changed.emit(self._history.can_undo, self._history.can_redo)

    def undo(self) -> None:
        cmd = self._history.undo()
        if cmd is None:
            return
        self._table_model.refresh_all()
        self._signals.issues_updated.emit()
        self._signals.history_changed.emit(self._history.can_undo, self._history.can_redo)
        self._signals.status_message.emit(f"Undone: {cmd.description}")

    def redo(self) -> None:
        cmd = self._history.redo()
        if cmd is None:
            return
        self._table_model.refresh_all()
        self._signals.issues_updated.emit()
        self._signals.history_changed.emit(self._history.can_undo, self._history.can_redo)
        self._signals.status_message.emit(f"Redone: {cmd.description}")

    @property
    def can_undo(self) -> bool:
        return self._history.can_undo

    @property
    def can_redo(self) -> bool:
        return self._history.can_redo

    @Slot(int, str, object)
    def _on_cell_edit(self, row: int, col: str, new_value: Any) -> None:
        """Handle direct cell edits from the table view."""
        self.apply_fix(row, col, new_value)
