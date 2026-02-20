"""Template Editor Dialog — 3-pane editor for YAML rule templates.

Layout:
  Left pane   — Column list (columns or column groups)
  Middle pane — Column Profile Editor (kind, flags, rule overrides)
  Right pane  — (future: Impact Preview)

Saves changes back to the template YAML file.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from spreadsheet_qa.core.template_manager import TemplateInfo
from spreadsheet_qa.ui.i18n import kind_label, preset_label, t

# Internal preset values (used in YAML) → display in combo
_PRESETS = [
    "(none)",
    "w3c_dtf_date",
    "uri",
    "email",
    "orcid",
    "creator_name",
    "custom_regex",
]

# Internal kind values
_KINDS = ["free_text_short", "free_text_long", "controlled", "structured", "list"]


class TemplateEditorDialog(QDialog):
    """3-pane template editor.

    Args:
        tmpl: The template to edit.
        parent: Parent widget.
    """

    def __init__(
        self,
        tmpl: TemplateInfo,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tmpl = tmpl
        self._data: dict = {}
        self._current_col: str | None = None

        self.setWindowTitle(t("tmpl_edit.title", name=tmpl.name))
        self.setMinimumSize(900, 600)
        self.resize(1050, 680)

        self._load_data()
        self._build_ui()
        self._populate_columns()

    # ------------------------------------------------------------------
    # Data I/O
    # ------------------------------------------------------------------

    def _load_data(self) -> None:
        try:
            self._data = yaml.safe_load(self._tmpl.path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            QMessageBox.critical(
                self,
                t("tmpl_edit.msg.load_error"),
                t("tmpl_edit.msg.load_body", exc=exc),
            )
            self._data = {}

    def _save_data(self) -> None:
        self._flush_current_column()
        try:
            self._tmpl.path.write_text(
                yaml.dump(self._data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                t("tmpl_edit.msg.save_error"),
                t("tmpl_edit.msg.save_body", exc=exc),
            )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)

        # Header
        header = QLabel(
            f"<b>{self._tmpl.name}</b>  "
            f"<span style='color:gray'>[{self._tmpl.scope}] {self._tmpl.type}</span><br>"
            f"<small>{self._tmpl.path}</small>"
        )
        header.setWordWrap(True)
        main_layout.addWidget(header)

        # 3-pane splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = self._build_left_pane()
        splitter.addWidget(left)

        self._mid_widget = self._build_middle_pane()
        splitter.addWidget(self._mid_widget)

        splitter.setSizes([220, 480])
        main_layout.addWidget(splitter, stretch=1)

        # Template-level rules section
        rules_group = self._build_rules_section()
        main_layout.addWidget(rules_group)

        # Dialog buttons
        btn_box = QDialogButtonBox()
        btn_save = btn_box.addButton(t("tmpl_edit.btn.save"), QDialogButtonBox.ButtonRole.AcceptRole)
        btn_cancel = btn_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        btn_save.clicked.connect(self._on_save)
        btn_cancel.clicked.connect(self.reject)
        main_layout.addWidget(btn_box)

    def _build_left_pane(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel(t("tmpl_edit.pane.left.title")))

        self._col_search = QLineEdit()
        self._col_search.setPlaceholderText(t("tmpl_edit.pane.left.filter"))
        self._col_search.textChanged.connect(self._filter_columns)
        layout.addWidget(self._col_search)

        self._col_list = QListWidget()
        self._col_list.currentRowChanged.connect(self._on_column_selected)
        layout.addWidget(self._col_list, stretch=1)

        return w

    def _build_middle_pane(self) -> QWidget:
        w = QWidget()
        self._mid_layout = QVBoxLayout(w)
        self._mid_layout.setContentsMargins(4, 0, 4, 0)

        self._col_header = QLabel(f"<i>{t('tmpl_edit.pane.mid.placeholder')}</i>")
        self._mid_layout.addWidget(self._col_header)

        form_group = QGroupBox(t("tmpl_edit.group.profile"))
        form = QFormLayout(form_group)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._combo_kind = QComboBox()
        for kind in _KINDS:
            self._combo_kind.addItem(kind_label(kind), userData=kind)
        form.addRow(t("tmpl_edit.label.kind"), self._combo_kind)

        self._chk_required = QCheckBox()
        form.addRow(t("tmpl_edit.label.required"), self._chk_required)

        self._chk_unique = QCheckBox()
        form.addRow(t("tmpl_edit.label.unique"), self._chk_unique)

        self._chk_multiline = QCheckBox()
        form.addRow(t("tmpl_edit.label.multiline"), self._chk_multiline)

        self._combo_preset = QComboBox()
        for preset in _PRESETS:
            self._combo_preset.addItem(preset_label(preset), userData=preset)
        self._combo_preset.currentIndexChanged.connect(self._on_preset_changed)
        form.addRow(t("tmpl_edit.label.preset"), self._combo_preset)

        self._edit_regex = QLineEdit()
        self._edit_regex.setPlaceholderText(t("preset.regex.placeholder"))
        form.addRow(t("tmpl_edit.label.regex"), self._edit_regex)

        self._edit_list_sep = QLineEdit()
        self._edit_list_sep.setPlaceholderText("|")
        self._edit_list_sep.setMaximumWidth(40)
        form.addRow(t("tmpl_edit.label.list_sep"), self._edit_list_sep)

        self._mid_layout.addWidget(form_group)

        # Rule overrides
        override_group = QGroupBox(t("tmpl_edit.group.overrides"))
        override_layout = QVBoxLayout(override_group)
        override_layout.addWidget(QLabel(t("tmpl_edit.overrides.help")))
        self._edit_overrides = QTextEdit()
        self._edit_overrides.setPlaceholderText(t("tmpl_edit.overrides.placeholder"))
        self._edit_overrides.setMaximumHeight(100)
        override_layout.addWidget(self._edit_overrides)
        self._mid_layout.addWidget(override_group)

        self._mid_layout.addStretch()

        self._set_form_enabled(False)

        return w

    def _build_rules_section(self) -> QWidget:
        group = QGroupBox(t("tmpl_edit.group.global_rules"))
        layout = QVBoxLayout(group)
        layout.addWidget(QLabel(t("tmpl_edit.global_rules.help")))
        rules = self._data.get("rules", {})
        rules_str = ", ".join(sorted(rules.keys())) if rules else t("tmpl_edit.active_rules.none")
        layout.addWidget(QLabel(t("tmpl_edit.active_rules", rules=rules_str)))
        return group

    # ------------------------------------------------------------------
    # Column list management
    # ------------------------------------------------------------------

    def _populate_columns(self) -> None:
        self._col_list.clear()
        column_groups = self._data.get("column_groups", {})
        columns = self._data.get("columns", {})

        items: list[str] = []
        if "*" in columns:
            items.append(t("tmpl_edit.wildcard"))
        for pattern in column_groups:
            items.append(f"{t('tmpl_edit.group_prefix')} {pattern}")
        for col in columns:
            if col != "*":
                items.append(col)

        for item in items:
            self._col_list.addItem(item)

    def _filter_columns(self, text: str) -> None:
        for i in range(self._col_list.count()):
            item = self._col_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    # ------------------------------------------------------------------
    # Column editor
    # ------------------------------------------------------------------

    def _on_column_selected(self, row: int) -> None:
        self._flush_current_column()

        if row < 0:
            self._set_form_enabled(False)
            self._current_col = None
            return

        item = self._col_list.item(row)
        if item is None:
            return

        label = item.text()
        self._set_form_enabled(True)

        wildcard_label = t("tmpl_edit.wildcard")
        group_prefix = t("tmpl_edit.group_prefix") + " "

        if label == wildcard_label:
            key = "*"
            source = "columns"
        elif label.startswith(group_prefix):
            key = label[len(group_prefix):]
            source = "column_groups"
        else:
            key = label
            source = "columns"

        self._current_col = f"{source}::{key}"
        self._col_header.setText(f"<b>{label}</b>")

        cfg: dict = {}
        if source == "columns":
            cfg = deepcopy(self._data.get("columns", {}).get(key, {}))
        else:
            cfg = deepcopy(self._data.get("column_groups", {}).get(key, {}))

        self._load_col_cfg(cfg)

    def _load_col_cfg(self, cfg: dict) -> None:
        # Kind: find combo index by stored internal value
        kind = cfg.get("kind", "free_text_short")
        for i in range(self._combo_kind.count()):
            if self._combo_kind.itemData(i) == kind:
                self._combo_kind.setCurrentIndex(i)
                break

        self._chk_required.setChecked(bool(cfg.get("required", False)))
        self._chk_unique.setChecked(bool(cfg.get("unique", False)))
        self._chk_multiline.setChecked(bool(cfg.get("multiline_ok", False)))

        # Preset: find combo index by stored internal value
        preset = cfg.get("preset", "(none)")
        for i in range(self._combo_preset.count()):
            if self._combo_preset.itemData(i) == preset:
                self._combo_preset.setCurrentIndex(i)
                break

        self._edit_regex.setText(cfg.get("regex", ""))
        self._edit_list_sep.setText(cfg.get("list_separator", ""))

        overrides = cfg.get("rule_overrides", {})
        lines: list[str] = []
        for rule_id, ov in overrides.items():
            parts = [rule_id + ":"]
            if "enabled" in ov:
                parts.append(f"enabled={str(ov['enabled']).lower()}")
            if "severity" in ov:
                parts.append(f"severity={ov['severity']}")
            lines.append(" ".join(parts))
        self._edit_overrides.setPlainText("\n".join(lines))

    def _flush_current_column(self) -> None:
        """Write current form values back to self._data."""
        if self._current_col is None:
            return

        source, key = self._current_col.split("::", 1)

        cfg: dict = {}
        # Kind: retrieve internal value from combo userData
        kind = self._combo_kind.currentData()
        if kind:
            cfg["kind"] = kind
        if self._chk_required.isChecked():
            cfg["required"] = True
        if self._chk_unique.isChecked():
            cfg["unique"] = True
        if self._chk_multiline.isChecked():
            cfg["multiline_ok"] = True
        preset = self._combo_preset.currentData()
        if preset and preset != "(none)":
            cfg["preset"] = preset
        regex = self._edit_regex.text().strip()
        if regex:
            cfg["regex"] = regex
        sep = self._edit_list_sep.text().strip()
        if sep:
            cfg["list_separator"] = sep

        overrides: dict = {}
        for line in self._edit_overrides.toPlainText().splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            rule_id, rest = line.split(":", 1)
            rule_id = rule_id.strip()
            ov: dict = {}
            for token in rest.split():
                if "=" in token:
                    k, v = token.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    if k == "enabled":
                        ov[k] = v.lower() in ("true", "1", "yes")
                    else:
                        ov[k] = v
            if ov:
                overrides[rule_id] = ov
        if overrides:
            cfg["rule_overrides"] = overrides

        if source == "columns":
            if "columns" not in self._data:
                self._data["columns"] = {}
            self._data["columns"][key] = cfg
        else:
            if "column_groups" not in self._data:
                self._data["column_groups"] = {}
            self._data["column_groups"][key] = cfg

    def _set_form_enabled(self, enabled: bool) -> None:
        for widget in [
            self._combo_kind, self._chk_required, self._chk_unique,
            self._chk_multiline, self._combo_preset, self._edit_regex,
            self._edit_list_sep, self._edit_overrides,
        ]:
            widget.setEnabled(enabled)

    def _on_preset_changed(self, idx: int) -> None:
        preset = self._combo_preset.itemData(idx)
        self._edit_regex.setEnabled(preset == "custom_regex")

    def select_column(self, col_name: str) -> None:
        """Pre-select a specific column in the list (called from main window)."""
        for i in range(self._col_list.count()):
            if self._col_list.item(i).text() == col_name:
                self._col_list.setCurrentRow(i)
                return

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        self._save_data()
        self.accept()
