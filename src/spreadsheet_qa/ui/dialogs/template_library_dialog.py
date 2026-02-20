"""Template Library dialog.

Lists all available templates (built-in, user, project) and lets the user
apply them, create new ones, duplicate, edit, delete, import, and export.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from spreadsheet_qa.core.template_manager import TemplateInfo, TemplateManager
from spreadsheet_qa.ui.i18n import t

if TYPE_CHECKING:
    from spreadsheet_qa.ui.controllers.load_controller import LoadController
    from spreadsheet_qa.ui.signals import AppSignals


class TemplateLibraryDialog(QDialog):
    """Template Library: lists all templates and provides management actions."""

    def __init__(
        self,
        load_ctrl: "LoadController",
        signals: "AppSignals",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._load_ctrl = load_ctrl
        self._signals = signals
        self._mgr = TemplateManager()
        self._templates: list[TemplateInfo] = []

        self.setWindowTitle(t("tmpl_lib.title"))
        self.setMinimumSize(760, 480)
        self.resize(860, 540)

        self._build_ui()
        self._refresh_table()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # -- Templates table --
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels([
            t("tmpl_lib.col.name"),
            t("tmpl_lib.col.scope"),
            t("tmpl_lib.col.type"),
            t("tmpl_lib.col.path"),
        ])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(self._on_edit)
        layout.addWidget(self._table, stretch=1)

        # -- Apply section --
        apply_group = QGroupBox(t("tmpl_lib.group.apply"))
        apply_layout = QVBoxLayout(apply_group)

        generic_row = QHBoxLayout()
        generic_row.addWidget(QLabel(t("tmpl_lib.label.base")))
        self._combo_generic = QComboBox()
        self._combo_generic.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        generic_row.addWidget(self._combo_generic)
        apply_layout.addLayout(generic_row)

        overlay_row = QHBoxLayout()
        self._chk_overlay = QCheckBox(t("tmpl_lib.label.overlay"))
        self._chk_overlay.setChecked(False)
        self._chk_overlay.toggled.connect(lambda checked: self._combo_overlay.setEnabled(checked))
        overlay_row.addWidget(self._chk_overlay)
        self._combo_overlay = QComboBox()
        self._combo_overlay.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._combo_overlay.setEnabled(False)
        overlay_row.addWidget(self._combo_overlay)
        apply_layout.addLayout(overlay_row)

        apply_btn = QPushButton(t("tmpl_lib.btn.apply"))
        apply_btn.clicked.connect(self._on_apply)
        apply_layout.addWidget(apply_btn)

        layout.addWidget(apply_group)

        # -- Side buttons --
        btn_layout = QHBoxLayout()

        self._btn_edit = QPushButton(t("tmpl_lib.btn.edit"))
        self._btn_edit.clicked.connect(self._on_edit)
        btn_layout.addWidget(self._btn_edit)

        self._btn_duplicate = QPushButton(t("tmpl_lib.btn.duplicate"))
        self._btn_duplicate.clicked.connect(self._on_duplicate)
        btn_layout.addWidget(self._btn_duplicate)

        self._btn_delete = QPushButton(t("tmpl_lib.btn.delete"))
        self._btn_delete.clicked.connect(self._on_delete)
        btn_layout.addWidget(self._btn_delete)

        btn_layout.addStretch()

        self._btn_import = QPushButton(t("tmpl_lib.btn.import"))
        self._btn_import.clicked.connect(self._on_import)
        btn_layout.addWidget(self._btn_import)

        self._btn_export = QPushButton(t("tmpl_lib.btn.export"))
        self._btn_export.clicked.connect(self._on_export)
        btn_layout.addWidget(self._btn_export)

        layout.addLayout(btn_layout)

        # -- Close button --
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Table management
    # ------------------------------------------------------------------

    def _refresh_table(self) -> None:
        self._templates = self._mgr.list_templates()
        self._table.setRowCount(len(self._templates))

        generics = [t_ for t_ in self._templates if t_.type == "generic"]
        overlays = [t_ for t_ in self._templates if t_.type == "overlay"]

        self._combo_generic.clear()
        for tmpl in generics:
            self._combo_generic.addItem(f"{tmpl.name} [{tmpl.scope}]", userData=tmpl.id)

        self._combo_overlay.clear()
        for tmpl in overlays:
            self._combo_overlay.addItem(f"{tmpl.name} [{tmpl.scope}]", userData=tmpl.id)

        # Set combos to current active template
        current_generic = self._load_ctrl.active_generic
        current_overlay = self._load_ctrl.active_overlay
        for i in range(self._combo_generic.count()):
            if self._combo_generic.itemData(i) == current_generic:
                self._combo_generic.setCurrentIndex(i)
                break
        if current_overlay:
            self._chk_overlay.setChecked(True)
            for i in range(self._combo_overlay.count()):
                if self._combo_overlay.itemData(i) == current_overlay:
                    self._combo_overlay.setCurrentIndex(i)
                    break

        scope_colors = {"builtin": "#e8f5e9", "user": "#e3f2fd", "project": "#fff8e1"}
        for row, tmpl in enumerate(self._templates):
            name_item = QTableWidgetItem(tmpl.name)
            scope_item = QTableWidgetItem(tmpl.scope)
            type_item = QTableWidgetItem(tmpl.type)
            path_item = QTableWidgetItem(str(tmpl.path))

            color = scope_colors.get(tmpl.scope, "#ffffff")
            from PySide6.QtGui import QColor
            for item in [name_item, scope_item, type_item, path_item]:
                item.setBackground(QColor(color))
            if tmpl.readonly:
                name_item.setToolTip(t("tmpl_lib.tooltip.readonly"))

            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, scope_item)
            self._table.setItem(row, 2, type_item)
            self._table.setItem(row, 3, path_item)

        self._table.resizeColumnToContents(0)
        self._table.resizeColumnToContents(1)
        self._table.resizeColumnToContents(2)

    def _selected_template(self) -> TemplateInfo | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._templates):
            return None
        return self._templates[row]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_apply(self) -> None:
        generic_id = self._combo_generic.currentData()
        overlay_id = self._combo_overlay.currentData() if self._chk_overlay.isChecked() else None
        if not generic_id:
            QMessageBox.warning(self, t("tmpl_lib.msg.no_template"), t("tmpl_lib.msg.select_base"))
            return
        self._load_ctrl.set_active_template(generic_id, overlay_id)
        overlay_label = f" + {overlay_id}" if overlay_id else ""
        self._signals.status_message.emit(
            t("tmpl_lib.msg.applied", id=generic_id, overlay=overlay_label)
        )

    def _on_edit(self) -> None:
        tmpl = self._selected_template()
        if tmpl is None:
            QMessageBox.information(
                self, t("tmpl_lib.msg.no_selection"), t("tmpl_lib.msg.select_to_edit")
            )
            return
        if tmpl.readonly:
            reply = QMessageBox.question(
                self,
                t("tmpl_lib.msg.readonly_title"),
                t("tmpl_lib.msg.readonly_body"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_duplicate()
            return
        self._open_editor(tmpl)

    def _open_editor(self, tmpl: TemplateInfo) -> None:
        from spreadsheet_qa.ui.dialogs.template_editor_dialog import TemplateEditorDialog
        dlg = TemplateEditorDialog(tmpl=tmpl, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_table()

    def _on_duplicate(self) -> None:
        tmpl = self._selected_template()
        if tmpl is None:
            QMessageBox.information(
                self, t("tmpl_lib.msg.no_selection"), t("tmpl_lib.msg.select_to_dup")
            )
            return

        user_dir = self._mgr.get_user_templates_dir()
        user_dir.mkdir(parents=True, exist_ok=True)

        stem = tmpl.id
        dest = user_dir / f"{stem}_copie.yml"
        counter = 1
        while dest.exists():
            dest = user_dir / f"{stem}_copie{counter}.yml"
            counter += 1

        try:
            import shutil
            shutil.copy2(tmpl.path, dest)
            import yaml
            data = yaml.safe_load(dest.read_text(encoding="utf-8")) or {}
            data["id"] = dest.stem
            data["name"] = tmpl.name + t("tmpl_lib.copy_suffix")
            data["scope"] = "user"
            dest.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, t("tmpl_lib.msg.dup_error"), str(exc))
            return

        self._refresh_table()
        for row, tmpl_ in enumerate(self._templates):
            if tmpl_.path == dest:
                self._table.setCurrentCell(row, 0)
                self._open_editor(tmpl_)
                break

    def _on_delete(self) -> None:
        tmpl = self._selected_template()
        if tmpl is None:
            return
        if tmpl.readonly:
            QMessageBox.warning(
                self, t("tmpl_lib.msg.cannot_delete"), t("tmpl_lib.msg.builtin_nodelete")
            )
            return
        reply = QMessageBox.question(
            self,
            t("tmpl_lib.msg.delete_title"),
            t("tmpl_lib.msg.delete_body", name=tmpl.name, path=tmpl.path),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            tmpl.path.unlink()
        except Exception as exc:
            QMessageBox.critical(self, t("tmpl_lib.msg.delete_error"), str(exc))
            return
        self._refresh_table()

    def _on_import(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            t("tmpl_lib.dialog.import"),
            str(Path.home()),
            "YAML files (*.yml *.yaml)",
        )
        if not path_str:
            return
        src = Path(path_str)
        user_dir = self._mgr.get_user_templates_dir()
        user_dir.mkdir(parents=True, exist_ok=True)
        dest = user_dir / src.name
        if dest.exists():
            reply = QMessageBox.question(
                self,
                t("tmpl_lib.msg.file_exists"),
                t("tmpl_lib.msg.overwrite", name=dest.name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            import shutil
            shutil.copy2(src, dest)
        except Exception as exc:
            QMessageBox.critical(self, t("tmpl_lib.msg.import_error"), str(exc))
            return
        self._refresh_table()

    def _on_export(self) -> None:
        tmpl = self._selected_template()
        if tmpl is None:
            QMessageBox.information(
                self, t("tmpl_lib.msg.no_selection"), t("tmpl_lib.msg.select_to_export")
            )
            return
        dest_str, _ = QFileDialog.getSaveFileName(
            self,
            t("tmpl_lib.dialog.export"),
            str(Path.home() / tmpl.path.name),
            "YAML files (*.yml)",
        )
        if not dest_str:
            return
        try:
            import shutil
            shutil.copy2(tmpl.path, Path(dest_str))
        except Exception as exc:
            QMessageBox.critical(self, t("tmpl_lib.msg.export_error"), str(exc))
