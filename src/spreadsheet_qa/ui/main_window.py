"""MainWindow: top-level Qt window with sidebar navigation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QStatusBar,
    QToolBar,
    QWidget,
)

from spreadsheet_qa.core.issue_store import IssueStore
from spreadsheet_qa.core.patch import NullPatchWriter
from spreadsheet_qa.core.project import NullProjectManager
from spreadsheet_qa.ui.controllers.export_controller import ExportController
from spreadsheet_qa.ui.controllers.fix_controller import FixController
from spreadsheet_qa.ui.controllers.load_controller import LoadController
from spreadsheet_qa.ui.controllers.project_controller import ProjectController
from spreadsheet_qa.ui.controllers.validation_controller import ValidationController
from spreadsheet_qa.ui.i18n import t
from spreadsheet_qa.ui.panels.find_fix_drawer import FindFixDrawer
from spreadsheet_qa.ui.panels.issues_panel import IssuesPanel
from spreadsheet_qa.ui.signals import AppSignals
from spreadsheet_qa.ui.table.table_model import SpreadsheetTableModel
from spreadsheet_qa.ui.table.table_view import SpreadsheetTableView


class MainWindow(QMainWindow):
    """Application main window."""

    def __init__(self, signals: AppSignals) -> None:
        super().__init__()
        self._signals = signals
        self.setWindowTitle(t("app.title"))
        self.setMinimumSize(1100, 700)
        self.resize(1400, 850)

        # Core data objects
        empty_df = pd.DataFrame()
        self._issue_store = IssueStore()
        self._table_model = SpreadsheetTableModel(empty_df, self._issue_store, signals)
        self._project_manager = NullProjectManager()

        # Controllers (order matters — LoadController needs ValidationController)
        self._validation_ctrl = ValidationController(
            self._table_model, self._issue_store, signals
        )
        self._fix_ctrl = FixController(
            self._table_model,
            self._issue_store,
            signals,
            self._validation_ctrl,
            patch_writer=NullPatchWriter(),
        )
        self._load_ctrl = LoadController(
            self._table_model,
            self._issue_store,
            signals,
            self,
            validation_ctrl=self._validation_ctrl,
        )
        self._project_ctrl = ProjectController(
            self._load_ctrl, signals, self, issue_store=self._issue_store
        )
        self._export_ctrl = ExportController(
            self._table_model, self._issue_store, signals, self
        )

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._build_toolbar()

        # Central widget: table view
        self._table_view = SpreadsheetTableView()
        self._table_view.setModel(self._table_model)
        self._table_view.column_context_menu_requested.connect(self._on_column_context_menu)

        # Issues dock (right)
        self._issues_panel = IssuesPanel(self._issue_store, self._signals, self)
        issues_dock = QDockWidget(t("dock.issues"), self)
        issues_dock.setObjectName("IssuesDock")
        issues_dock.setWidget(self._issues_panel)
        issues_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, issues_dock)
        self._issues_dock = issues_dock

        # Find & Fix dock (bottom)
        self._find_fix_drawer = FindFixDrawer(self._issue_store, self._signals, self)
        self._find_fix_drawer.set_fix_controller(self._fix_ctrl)
        ff_dock = QDockWidget(t("dock.findfix"), self)
        ff_dock.setObjectName("FindFixDock")
        ff_dock.setWidget(self._find_fix_drawer)
        ff_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, ff_dock)
        ff_dock.hide()
        self._ff_dock = ff_dock

        self.setCentralWidget(self._table_view)

        # Status bar
        self._status_bar = QStatusBar()
        self._status_label = QLabel(t("app.ready"))
        self._status_bar.addWidget(self._status_label, 1)
        self.setStatusBar(self._status_bar)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main toolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        # Open
        self._act_open = QAction(t("action.open"), self)
        self._act_open.setShortcut(QKeySequence.StandardKey.Open)
        self._act_open.setToolTip(t("action.open.tooltip"))
        self._act_open.triggered.connect(self._load_ctrl.open_file_dialog)
        tb.addAction(self._act_open)

        tb.addSeparator()

        # Validate
        self._act_validate = QAction(t("action.validate"), self)
        self._act_validate.setShortcut(QKeySequence("Ctrl+Shift+V"))
        self._act_validate.setToolTip(t("action.validate.tooltip"))
        self._act_validate.triggered.connect(self._validation_ctrl.run_full)
        tb.addAction(self._act_validate)

        # Toggle Find & Fix
        self._act_findfix = QAction(t("action.findfix"), self)
        self._act_findfix.setShortcut(QKeySequence("Ctrl+F"))
        self._act_findfix.setToolTip(t("action.findfix.tooltip"))
        self._act_findfix.triggered.connect(self._toggle_findfix)
        tb.addAction(self._act_findfix)

        tb.addSeparator()

        # Undo / Redo
        self._act_undo = QAction(t("action.undo"), self)
        self._act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._act_undo.setEnabled(False)
        self._act_undo.triggered.connect(self._fix_ctrl.undo)
        tb.addAction(self._act_undo)

        self._act_redo = QAction(t("action.redo"), self)
        self._act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self._act_redo.setEnabled(False)
        self._act_redo.triggered.connect(self._fix_ctrl.redo)
        tb.addAction(self._act_redo)

        tb.addSeparator()

        # Templates
        self._act_templates = QAction(t("action.templates"), self)
        self._act_templates.setToolTip(t("action.templates.tooltip"))
        self._act_templates.triggered.connect(self._on_open_templates)
        tb.addAction(self._act_templates)

        # Export
        self._act_export = QAction(t("action.export"), self)
        self._act_export.setShortcut(QKeySequence("Ctrl+E"))
        self._act_export.setToolTip(t("action.export.tooltip"))
        self._act_export.triggered.connect(self._on_export)
        tb.addAction(self._act_export)

        # Toggle issues
        self._act_issues = QAction(t("action.issues_panel"), self)
        self._act_issues.setShortcut(QKeySequence("Ctrl+I"))
        self._act_issues.triggered.connect(lambda: self._issues_dock.setVisible(
            not self._issues_dock.isVisible()
        ))
        tb.addAction(self._act_issues)

        # Build menu bar
        menubar = self.menuBar()

        file_menu = menubar.addMenu(t("menu.file"))
        file_menu.addAction(self._act_open)

        act_open_project = QAction(t("menu.file.open_project"), self)
        act_open_project.triggered.connect(self._project_ctrl.open_project_dialog)
        file_menu.addAction(act_open_project)

        act_save_project = QAction(t("menu.file.save_project"), self)
        act_save_project.triggered.connect(self._project_ctrl.save_project_as_dialog)
        file_menu.addAction(act_save_project)

        file_menu.addSeparator()
        file_menu.addAction(self._act_export)
        file_menu.addSeparator()
        quit_act = QAction(t("menu.file.quit"), self)
        quit_act.setShortcut(QKeySequence.StandardKey.Quit)
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        edit_menu = menubar.addMenu(t("menu.edit"))
        edit_menu.addAction(self._act_undo)
        edit_menu.addAction(self._act_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self._act_findfix)

        view_menu = menubar.addMenu(t("menu.view"))
        view_menu.addAction(self._act_issues)
        view_menu.addAction(self._act_findfix)

        validate_menu = menubar.addMenu(t("menu.validate"))
        validate_menu.addAction(self._act_validate)

        tools_menu = menubar.addMenu(t("menu.tools"))
        tools_menu.addAction(self._act_templates)

    # ------------------------------------------------------------------
    # Signal connections
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._signals.status_message.connect(self._status_label.setText)
        self._signals.history_changed.connect(self._on_history_changed)
        self._signals.dataset_loaded.connect(self._on_dataset_loaded)
        self._signals.issue_selected.connect(self._on_issue_selected)
        self._signals.validation_started.connect(
            lambda: self._status_label.setText(t("status.validating"))
        )
        self._signals.template_changed.connect(self._on_template_changed)
        self._signals.issue_status_changed.connect(self._on_issue_status_changed)
        self._signals.project_saved.connect(self._on_project_saved)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_history_changed(self, can_undo: bool, can_redo: bool) -> None:
        self._act_undo.setEnabled(can_undo)
        self._act_redo.setEnabled(can_redo)
        if can_undo:
            self._act_undo.setToolTip(
                t("action.undo.tooltip", desc=self._fix_ctrl._history.undo_description)
            )
        if can_redo:
            self._act_redo.setToolTip(
                t("action.redo.tooltip", desc=self._fix_ctrl._history.redo_description)
            )

    def _on_dataset_loaded(self, meta) -> None:
        self._find_fix_drawer.set_dataframe(self._table_model.df)
        self.setWindowTitle(f"Tablerreur — {Path(meta.file_path).name}")

    def _on_issue_selected(self, issue) -> None:
        """Scroll table view to the issue's cell."""
        df = self._table_model.df
        if issue.col in df.columns:
            col_idx = list(df.columns).index(issue.col)
            self._table_view.scroll_to_cell(issue.row, col_idx)

    def _on_issue_status_changed(self, issue_id: str, status_value: str) -> None:
        """Persist EXCEPTED/IGNORED status changes to exceptions.yml."""
        if status_value == "EXCEPTED":
            self._project_manager.add_exception(issue_id)
        elif status_value == "IGNORED":
            self._project_manager.add_ignored(issue_id)

    def _on_project_saved(self, folder_path: str) -> None:
        """Switch to the real ProjectManager once a project folder is set."""
        from spreadsheet_qa.core.project import ProjectManager
        self._project_manager = ProjectManager(Path(folder_path))
        self._fix_ctrl.set_project_manager(self._project_manager)

    def _on_column_context_menu(self, section: int) -> None:
        """Show a context menu for a right-clicked column header."""
        df = self._table_model.df
        if df is None or section >= len(df.columns):
            return
        col_name = df.columns[section]
        col_cfg = self._validation_ctrl._config.get("columns", {}).get(col_name, {})

        menu = QMenu(self)
        menu.setTitle(t("col_menu.title", name=col_name))

        # Set kind submenu
        kind_menu = menu.addMenu(t("col_menu.set_kind"))
        for kind in ("free_text_short", "free_text_long", "controlled", "structured", "list"):
            from spreadsheet_qa.ui.i18n import kind_label
            act = kind_menu.addAction(kind_label(kind))
            act.setCheckable(True)
            act.setChecked(col_cfg.get("kind") == kind)
            act.triggered.connect(
                lambda checked, k=kind: self._validation_ctrl.set_column_override(
                    col_name, {"kind": k}
                )
            )

        menu.addSeparator()

        # Toggle Required
        req_act = menu.addAction(t("col_menu.required"))
        req_act.setCheckable(True)
        req_act.setChecked(bool(col_cfg.get("required", False)))
        req_act.triggered.connect(
            lambda checked: self._validation_ctrl.set_column_override(
                col_name, {"required": checked}
            )
        )

        # Toggle Unique
        uniq_act = menu.addAction(t("col_menu.unique"))
        uniq_act.setCheckable(True)
        uniq_act.setChecked(bool(col_cfg.get("unique", False)))
        uniq_act.triggered.connect(
            lambda checked: self._validation_ctrl.set_column_override(
                col_name, {"unique": checked}
            )
        )

        # Toggle Multiline
        ml_act = menu.addAction(t("col_menu.multiline"))
        ml_act.setCheckable(True)
        ml_act.setChecked(bool(col_cfg.get("multiline_ok", False)))
        ml_act.triggered.connect(
            lambda checked: self._validation_ctrl.set_column_override(
                col_name, {"multiline_ok": checked}
            )
        )

        menu.addSeparator()

        edit_act = menu.addAction(t("col_menu.edit_template"))
        edit_act.triggered.connect(lambda: self._open_template_editor_for_column(col_name))

        from PySide6.QtGui import QCursor
        menu.exec(QCursor.pos())

    def _on_template_changed(self, generic_id: str, overlay_id: str) -> None:
        overlay_label = f" + {overlay_id}" if overlay_id else ""
        self._signals.status_message.emit(
            t("status.template_changed", id=generic_id, overlay=overlay_label)
        )

    def _open_template_editor_for_column(self, col_name: str) -> None:
        """Open the Template Editor focused on the given column."""
        from spreadsheet_qa.ui.dialogs.template_editor_dialog import TemplateEditorDialog
        dialog = TemplateEditorDialog(
            load_ctrl=self._load_ctrl,
            signals=self._signals,
            parent=self,
        )
        if hasattr(dialog, "select_column"):
            dialog.select_column(col_name)
        dialog.exec()

    def _toggle_findfix(self) -> None:
        self._ff_dock.setVisible(not self._ff_dock.isVisible())

    def _on_open_templates(self) -> None:
        from spreadsheet_qa.ui.dialogs.template_library_dialog import TemplateLibraryDialog

        dialog = TemplateLibraryDialog(
            load_ctrl=self._load_ctrl,
            signals=self._signals,
            parent=self,
        )
        dialog.exec()

    def _on_export(self) -> None:
        from spreadsheet_qa.ui.dialogs.export_dialog import ExportDialog
        from datetime import datetime

        dialog = ExportDialog(self)
        if dialog.exec() != ExportDialog.DialogCode.Accepted:
            return
        if dialog.output_dir is None:
            return

        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        out = dialog.output_dir
        out.mkdir(parents=True, exist_ok=True)

        df = self._table_model.df
        issues = self._issue_store.all_issues()
        meta = self._load_ctrl.current_meta
        errors: list[str] = []

        if dialog.export_xlsx:
            try:
                from spreadsheet_qa.core.exporters import XLSXExporter
                XLSXExporter().export(df, out / f"nettoyé_{stamp}.xlsx")
            except Exception as exc:
                errors.append(str(exc))

        if dialog.export_csv:
            try:
                from spreadsheet_qa.core.exporters import CSVExporter
                CSVExporter().export(df, out / f"nettoyé_{stamp}.csv", bom=dialog.csv_bom)
            except Exception as exc:
                errors.append(str(exc))

        if dialog.export_report:
            try:
                from spreadsheet_qa.core.exporters import TXTReporter
                TXTReporter().export(issues, out / f"rapport_{stamp}.txt", meta=meta)
            except Exception as exc:
                errors.append(str(exc))

        if dialog.export_issues_csv:
            try:
                from spreadsheet_qa.core.exporters import IssuesCSVExporter
                IssuesCSVExporter().export(issues, out / f"problèmes_{stamp}.csv", meta=meta)
            except Exception as exc:
                errors.append(str(exc))

        if errors:
            QMessageBox.warning(self, t("export.error_title"), "\n".join(errors))
        else:
            self._signals.status_message.emit(t("status.export_done", path=out))
