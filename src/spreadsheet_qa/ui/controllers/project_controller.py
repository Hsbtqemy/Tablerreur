"""ProjectController: orchestrates opening and saving project folders."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from spreadsheet_qa.core.project import ProjectManager
from spreadsheet_qa.ui.i18n import t

if TYPE_CHECKING:
    from spreadsheet_qa.core.issue_store import IssueStore
    from spreadsheet_qa.core.models import DatasetMeta
    from spreadsheet_qa.ui.controllers.load_controller import LoadController
    from spreadsheet_qa.ui.signals import AppSignals


class ProjectController:
    """Manage open-project and save-project flows."""

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
            t("project.open_dialog"),
            str(Path.home()),
        )
        if not folder_str:
            return
        self.open_project(Path(folder_str))

    def open_project(self, folder: Path) -> bool:
        """Open an existing project from *folder*."""
        yml_path = folder / "project.yml"
        if not yml_path.exists():
            QMessageBox.warning(
                self._parent,
                t("project.not_a_project"),
                t("project.no_yml", folder=folder),
            )
            return False

        try:
            pm = ProjectManager(folder)
            yml = pm.load_project_yml()
        except Exception as exc:
            QMessageBox.critical(
                self._parent,
                t("project.error_title"),
                t("project.error_body", exc=exc),
            )
            return False

        source_file = yml.get("source_file")
        if not source_file or not Path(source_file).exists():
            name = Path(source_file).name if source_file else None
            fallback = (folder / "input" / name) if name else None
            if fallback and fallback.exists():
                source_file = str(fallback)
            else:
                QMessageBox.warning(
                    self._parent,
                    t("project.missing_file"),
                    t("project.missing_file_body", path=source_file),
                )
                return False

        header_row = max(0, int(yml.get("header_row", 1)) - 1)
        sheet_name = yml.get("sheet_name") or None
        encoding = yml.get("encoding") or None
        delimiter = yml.get("delimiter") or None

        generic_id = yml.get("active_generic_template", "generic_default")
        overlay_id = yml.get("active_overlay_template") or None

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

        if self._issue_store is not None:
            pm.apply_exceptions_to_store(self._issue_store)
            self._signals.issues_updated.emit()

        self._signals.template_changed.emit(generic_id, overlay_id or "")
        self._signals.project_saved.emit(str(folder))
        self._signals.status_message.emit(t("status.project_opened", name=folder.name))
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
                t("project.no_file_title"),
                t("project.no_file_body"),
            )
            return

        folder_str = QFileDialog.getExistingDirectory(
            self._parent,
            t("project.save_dialog"),
            str(Path.home()),
        )
        if not folder_str:
            return
        self.save_project_as(Path(folder_str))

    def save_project_as(self, folder: Path) -> bool:
        """Save current state as a project in *folder*."""
        meta = self._load_ctrl.current_meta
        if meta is None:
            return False

        try:
            pm = ProjectManager(folder)
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
                t("project.save_error"),
                t("project.save_error_body", exc=exc),
            )
            return False

        self._project_manager = pm
        self._signals.project_saved.emit(str(folder))
        self._signals.status_message.emit(t("status.project_saved", path=folder))
        return True

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def project_manager(self) -> ProjectManager | None:
        return self._project_manager
