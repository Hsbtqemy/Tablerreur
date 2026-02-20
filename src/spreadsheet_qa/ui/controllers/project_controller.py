"""ProjectController: orchestrates opening and saving project folders."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from spreadsheet_qa.core.project import ProjectManager

if TYPE_CHECKING:
    from spreadsheet_qa.core.issue_store import IssueStore
    from spreadsheet_qa.core.models import DatasetMeta
    from spreadsheet_qa.ui.controllers.load_controller import LoadController
    from spreadsheet_qa.ui.signals import AppSignals


class ProjectController:
    """Manage open-project and save-project flows.

    This controller reads/writes ``project.yml`` and restores application state
    (file path, header row, templates) when opening an existing project.
    """

    def __init__(
        self,
        load_ctrl: "LoadController",
        signals: "AppSignals",
        parent_widget: QWidget,
        issue_store: "IssueStore | None" = None,
    ) -> None:
        self._load_ctrl = load_ctrl
        self._signals = signals
        self._parent = parent_widget
        self._issue_store = issue_store
        self._project_manager: ProjectManager | None = None

    # ------------------------------------------------------------------
    # Open project
    # ------------------------------------------------------------------

    def open_project_dialog(self) -> None:
        """Prompt user to select a project folder, then open it."""
        folder_str = QFileDialog.getExistingDirectory(
            self._parent,
            "Open Project Folder",
            str(Path.home()),
        )
        if not folder_str:
            return
        self.open_project(Path(folder_str))

    def open_project(self, folder: Path) -> bool:
        """Open an existing project from *folder*.

        Reads ``project.yml``, loads the source file, restores templates and
        header row, then triggers validation.

        Returns:
            True on success, False if the project could not be opened.
        """
        yml_path = folder / "project.yml"
        if not yml_path.exists():
            QMessageBox.warning(
                self._parent,
                "Not a project folder",
                f"No project.yml found in:\n{folder}",
            )
            return False

        try:
            pm = ProjectManager(folder)
            yml = pm.load_project_yml()
        except Exception as exc:
            QMessageBox.critical(
                self._parent,
                "Project error",
                f"Could not read project:\n{exc}",
            )
            return False

        source_file = yml.get("source_file")
        if not source_file or not Path(source_file).exists():
            # Try looking inside the project's input/ directory
            name = Path(source_file).name if source_file else None
            fallback = (folder / "input" / name) if name else None
            if fallback and fallback.exists():
                source_file = str(fallback)
            else:
                QMessageBox.warning(
                    self._parent,
                    "Missing source file",
                    f"Source file not found:\n{source_file}",
                )
                return False

        # header_row in project.yml is 1-based; LoadController uses 0-based
        header_row = max(0, int(yml.get("header_row", 1)) - 1)
        sheet_name = yml.get("sheet_name") or None
        encoding = yml.get("encoding") or None
        delimiter = yml.get("delimiter") or None

        # Restore template selection before loading (so config is ready)
        generic_id = yml.get("active_generic_template", "generic_default")
        overlay_id = yml.get("active_overlay_template") or None

        # Update load controller template state without triggering revalidation yet
        self._load_ctrl._active_generic = generic_id
        self._load_ctrl._active_overlay = overlay_id

        ok = self._load_ctrl.load_file(
            path=source_file,
            header_row=header_row,
            sheet_name=sheet_name,
            encoding_hint=encoding,
            delimiter_hint=delimiter,
        )
        if not ok:
            return False

        self._project_manager = pm

        # Restore EXCEPTED/IGNORED statuses from exceptions.yml (after validation ran)
        if self._issue_store is not None:
            pm.apply_exceptions_to_store(self._issue_store)
            self._signals.issues_updated.emit()

        # Notify listeners of the restored template selection
        self._signals.template_changed.emit(generic_id, overlay_id or "")

        self._signals.project_saved.emit(str(folder))
        self._signals.status_message.emit(f"Project opened: {folder.name}")
        return True

    # ------------------------------------------------------------------
    # Save project
    # ------------------------------------------------------------------

    def save_project_as_dialog(self) -> None:
        """Prompt user to choose a folder, then save project there."""
        meta = self._load_ctrl.current_meta
        if meta is None:
            QMessageBox.information(
                self._parent,
                "No file loaded",
                "Open a file first before saving a project.",
            )
            return

        folder_str = QFileDialog.getExistingDirectory(
            self._parent,
            "Save Project As — Choose Folder",
            str(Path.home()),
        )
        if not folder_str:
            return
        self.save_project_as(Path(folder_str))

    def save_project_as(self, folder: Path) -> bool:
        """Save current state as a project in *folder*.

        Creates the project structure, copies the source file to ``input/``,
        and writes ``project.yml``.

        Returns:
            True on success, False on error.
        """
        meta = self._load_ctrl.current_meta
        if meta is None:
            return False

        try:
            pm = ProjectManager(folder)
            # Copy source file into project
            src_path = Path(meta.file_path)
            if src_path.exists():
                pm.copy_input_file(src_path)

            pm.save_project_yml(
                meta=meta,
                active_generic_template=self._load_ctrl.active_generic,
                active_overlay_template=self._load_ctrl.active_overlay,
            )
        except Exception as exc:
            QMessageBox.critical(
                self._parent,
                "Save error",
                f"Could not save project:\n{exc}",
            )
            return False

        self._project_manager = pm
        self._signals.project_saved.emit(str(folder))
        self._signals.status_message.emit(f"Project saved: {folder}")
        return True

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def project_manager(self) -> ProjectManager | None:
        return self._project_manager
