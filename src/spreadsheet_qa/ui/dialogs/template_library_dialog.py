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

if TYPE_CHECKING:
    from spreadsheet_qa.ui.controllers.load_controller import LoadController
    from spreadsheet_qa.ui.signals import AppSignals


class TemplateLibraryDialog(QDialog):
    """Template Library: lists all templates and provides management actions.

    The dialog shows:
    - A table of available templates (name / scope / type / path)
    - Action buttons: Apply, New, Duplicate, Edit, Delete, Import, Export

    "Apply" selects the highlighted generic template (and optional overlay)
    as the active template and triggers revalidation.
    """

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

        self.setWindowTitle("Template Library")
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
        self._table.setHorizontalHeaderLabels(["Name", "Scope", "Type", "Path"])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(self._on_edit)
        layout.addWidget(self._table, stretch=1)

        # -- Apply section --
        apply_group = QGroupBox("Apply template")
        apply_layout = QVBoxLayout(apply_group)

        generic_row = QHBoxLayout()
        generic_row.addWidget(QLabel("Base template:"))
        self._combo_generic = QComboBox()
        self._combo_generic.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        generic_row.addWidget(self._combo_generic)
        apply_layout.addLayout(generic_row)

        overlay_row = QHBoxLayout()
        self._chk_overlay = QCheckBox("Overlay:")
        self._chk_overlay.setChecked(False)
        self._chk_overlay.toggled.connect(lambda checked: self._combo_overlay.setEnabled(checked))
        overlay_row.addWidget(self._chk_overlay)
        self._combo_overlay = QComboBox()
        self._combo_overlay.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._combo_overlay.setEnabled(False)
        overlay_row.addWidget(self._combo_overlay)
        apply_layout.addLayout(overlay_row)

        apply_btn = QPushButton("Apply && Validate")
        apply_btn.clicked.connect(self._on_apply)
        apply_layout.addWidget(apply_btn)

        layout.addWidget(apply_group)

        # -- Side buttons --
        btn_layout = QHBoxLayout()

        self._btn_edit = QPushButton("Edit…")
        self._btn_edit.clicked.connect(self._on_edit)
        btn_layout.addWidget(self._btn_edit)

        self._btn_duplicate = QPushButton("Duplicate")
        self._btn_duplicate.clicked.connect(self._on_duplicate)
        btn_layout.addWidget(self._btn_duplicate)

        self._btn_delete = QPushButton("Delete")
        self._btn_delete.clicked.connect(self._on_delete)
        btn_layout.addWidget(self._btn_delete)

        btn_layout.addStretch()

        self._btn_import = QPushButton("Import…")
        self._btn_import.clicked.connect(self._on_import)
        btn_layout.addWidget(self._btn_import)

        self._btn_export = QPushButton("Export…")
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

        generics = [t for t in self._templates if t.type == "generic"]
        overlays = [t for t in self._templates if t.type == "overlay"]

        self._combo_generic.clear()
        for t in generics:
            self._combo_generic.addItem(f"{t.name} [{t.scope}]", userData=t.id)

        self._combo_overlay.clear()
        for t in overlays:
            self._combo_overlay.addItem(f"{t.name} [{t.scope}]", userData=t.id)

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
                name_item.setToolTip("Built-in template (read-only). Duplicate to edit.")

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
            QMessageBox.warning(self, "No template", "Please select a base template.")
            return
        self._load_ctrl.set_active_template(generic_id, overlay_id)
        self._signals.status_message.emit(
            f"Template applied: {generic_id}"
            + (f" + {overlay_id}" if overlay_id else "")
        )

    def _on_edit(self) -> None:
        tmpl = self._selected_template()
        if tmpl is None:
            QMessageBox.information(self, "No selection", "Please select a template to edit.")
            return
        if tmpl.readonly:
            reply = QMessageBox.question(
                self,
                "Read-only template",
                "Built-in templates cannot be edited directly.\n\nDuplicate it first?",
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
            QMessageBox.information(self, "No selection", "Please select a template to duplicate.")
            return

        user_dir = self._mgr.get_user_templates_dir()
        user_dir.mkdir(parents=True, exist_ok=True)

        # Generate a unique name
        stem = tmpl.id
        dest = user_dir / f"{stem}_copy.yml"
        counter = 1
        while dest.exists():
            dest = user_dir / f"{stem}_copy{counter}.yml"
            counter += 1

        try:
            import shutil
            shutil.copy2(tmpl.path, dest)
            # Patch the id and scope in the copy
            import yaml
            data = yaml.safe_load(dest.read_text(encoding="utf-8")) or {}
            data["id"] = dest.stem
            data["name"] = f"{tmpl.name} (copy)"
            data["scope"] = "user"
            dest.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "Duplicate error", str(exc))
            return

        self._refresh_table()
        # Select and open the new template
        for row, t in enumerate(self._templates):
            if t.path == dest:
                self._table.setCurrentCell(row, 0)
                self._open_editor(t)
                break

    def _on_delete(self) -> None:
        tmpl = self._selected_template()
        if tmpl is None:
            return
        if tmpl.readonly:
            QMessageBox.warning(self, "Cannot delete", "Built-in templates cannot be deleted.")
            return
        reply = QMessageBox.question(
            self,
            "Delete template",
            f"Delete template '{tmpl.name}'?\nThis will remove:\n{tmpl.path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            tmpl.path.unlink()
        except Exception as exc:
            QMessageBox.critical(self, "Delete error", str(exc))
            return
        self._refresh_table()

    def _on_import(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Import Template", str(Path.home()), "YAML files (*.yml *.yaml)"
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
                "File exists",
                f"{dest.name} already exists in user templates. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            import shutil
            shutil.copy2(src, dest)
        except Exception as exc:
            QMessageBox.critical(self, "Import error", str(exc))
            return
        self._refresh_table()

    def _on_export(self) -> None:
        tmpl = self._selected_template()
        if tmpl is None:
            QMessageBox.information(self, "No selection", "Please select a template to export.")
            return
        dest_str, _ = QFileDialog.getSaveFileName(
            self, "Export Template", str(Path.home() / tmpl.path.name), "YAML files (*.yml)"
        )
        if not dest_str:
            return
        try:
            import shutil
            shutil.copy2(tmpl.path, Path(dest_str))
        except Exception as exc:
            QMessageBox.critical(self, "Export error", str(exc))
