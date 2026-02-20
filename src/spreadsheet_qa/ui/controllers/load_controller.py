"""LoadController: orchestrates file loading sequence."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox, QWidget

from spreadsheet_qa.core.dataset import DatasetLoader
from spreadsheet_qa.core.template_manager import TemplateManager
from spreadsheet_qa.ui.dialogs.load_dialog import LoadDialog

if TYPE_CHECKING:
    from spreadsheet_qa.core.issue_store import IssueStore
    from spreadsheet_qa.ui.controllers.validation_controller import ValidationController
    from spreadsheet_qa.ui.signals import AppSignals
    from spreadsheet_qa.ui.table.table_model import SpreadsheetTableModel


class LoadController:
    """Manages the file-open flow: dialog → DatasetLoader → model update."""

    def __init__(
        self,
        table_model: "SpreadsheetTableModel",
        issue_store: "IssueStore",
        signals: "AppSignals",
        parent_widget: QWidget,
        validation_ctrl: "ValidationController | None" = None,
        template_manager: TemplateManager | None = None,
    ) -> None:
        self._table_model = table_model
        self._issue_store = issue_store
        self._signals = signals
        self._parent = parent_widget
        self._loader = DatasetLoader()
        self._validation_ctrl = validation_ctrl
        self._template_manager = template_manager or TemplateManager()
        self._current_meta = None

        # Active template state
        self._active_generic: str = "generic_default"
        self._active_overlay: str | None = None

    # ------------------------------------------------------------------
    # Template selection
    # ------------------------------------------------------------------

    def set_active_template(
        self,
        generic_id: str,
        overlay_id: str | None = None,
    ) -> None:
        """Change the active template and trigger revalidation if a file is loaded."""
        self._active_generic = generic_id
        self._active_overlay = overlay_id
        self._signals.template_changed.emit(generic_id, overlay_id or "")

        if self._current_meta is not None:
            self._apply_template_and_revalidate()

    def _apply_template_and_revalidate(self) -> None:
        """Compile active template config and push to ValidationController."""
        if self._validation_ctrl is None:
            return
        df = self._table_model.df
        column_names = list(df.columns) if df is not None else []
        config = self._template_manager.compile_config(
            generic_id=self._active_generic,
            overlay_id=self._active_overlay,
            column_names=column_names,
        )
        self._validation_ctrl.set_config(config)
        self._validation_ctrl.run_full()

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def open_file_dialog(self) -> None:
        """Show the load dialog and load the selected file."""
        dialog = LoadDialog(self._parent)
        if dialog.exec() != LoadDialog.DialogCode.Accepted:
            return
        if not dialog.file_path:
            return

        self.load_file(
            path=dialog.file_path,
            header_row=dialog.header_row,
            sheet_name=dialog.sheet_name,
            encoding_hint=dialog.encoding_hint,
            delimiter_hint=dialog.delimiter_hint,
        )

    def load_file(
        self,
        path: str | Path,
        header_row: int = 0,
        sheet_name: str | None = None,
        encoding_hint: str | None = None,
        delimiter_hint: str | None = None,
    ) -> bool:
        """Load a file directly (e.g. from project.yml or drag-and-drop)."""
        try:
            df, meta = self._loader.load(
                path=path,
                header_row=header_row,
                sheet_name=sheet_name,
                encoding_hint=encoding_hint,
                delimiter_hint=delimiter_hint,
            )
        except Exception as exc:
            QMessageBox.critical(
                self._parent,
                "Load error",
                f"Could not load file:\n{exc}",
            )
            return False

        self._current_meta = meta
        self._table_model.replace_dataframe(df)
        self._issue_store.replace_all([])

        # Compile and apply template config before emitting dataset_loaded so
        # ValidationController has the right config when validation fires.
        if self._validation_ctrl is not None:
            column_names = list(df.columns)
            config = self._template_manager.compile_config(
                generic_id=self._active_generic,
                overlay_id=self._active_overlay,
                column_names=column_names,
            )
            self._validation_ctrl.set_config(config)

        self._signals.dataset_loaded.emit(meta)
        self._signals.status_message.emit(
            f"Loaded: {Path(meta.file_path).name}  "
            f"({meta.original_shape[0]} rows × {meta.original_shape[1]} cols)"
        )
        return True

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_meta(self):
        return self._current_meta

    @property
    def active_generic(self) -> str:
        return self._active_generic

    @property
    def active_overlay(self) -> str | None:
        return self._active_overlay
