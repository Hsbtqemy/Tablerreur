"""LoadDialog: file picker with header-row selection and CSV preview."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from spreadsheet_qa.core.dataset import DatasetLoader, get_xlsx_sheet_names, preview_header_rows
from spreadsheet_qa.ui.i18n import t


class LoadDialog(QDialog):
    """Dialog for selecting a CSV/XLSX file and configuring import options."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("load.title"))
        self.setMinimumSize(750, 500)

        self._file_path: str | None = None
        self._sheet_names: list[str] = []
        self._preview_rows: list[list[str]] = []

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # File selection
        file_box = QGroupBox(t("load.group.file"))
        file_layout = QHBoxLayout(file_box)
        self._path_edit = QLineEdit()
        self._path_edit.setReadOnly(True)
        self._path_edit.setPlaceholderText(t("load.placeholder.no_file"))
        browse_btn = QPushButton(t("load.btn.browse"))
        browse_btn.clicked.connect(self._browse)
        file_layout.addWidget(self._path_edit, 1)
        file_layout.addWidget(browse_btn)
        layout.addWidget(file_box)

        # Import options
        opts_box = QGroupBox(t("load.group.options"))
        opts_layout = QFormLayout(opts_box)

        # Sheet selector (XLSX only)
        self._sheet_combo = QComboBox()
        self._sheet_combo.setVisible(False)
        self._sheet_label = QLabel(t("load.label.sheet"))
        self._sheet_label.setVisible(False)
        self._sheet_combo.currentIndexChanged.connect(self._on_options_changed)
        opts_layout.addRow(self._sheet_label, self._sheet_combo)

        # Header row spinner (1-based for UI)
        self._header_spin = QSpinBox()
        self._header_spin.setMinimum(1)
        self._header_spin.setMaximum(100)
        self._header_spin.setValue(1)
        self._header_spin.setToolTip(t("load.tooltip.header_row"))
        self._header_spin.valueChanged.connect(self._on_options_changed)
        opts_layout.addRow(t("load.label.header_row"), self._header_spin)

        # Encoding hint
        self._encoding_combo = QComboBox()
        self._encoding_combo.addItems([
            t("load.encoding.auto"), "utf-8", "utf-8-sig", "latin-1", "cp1252"
        ])
        opts_layout.addRow(t("load.label.encoding"), self._encoding_combo)

        # Delimiter hint (CSV only)
        self._delim_combo = QComboBox()
        self._delim_combo.addItems([t("load.delimiter.auto"), ";", ",", "\\t", "|"])
        self._delim_label = QLabel(t("load.label.delimiter"))
        opts_layout.addRow(self._delim_label, self._delim_combo)

        layout.addWidget(opts_box)

        # Preview
        preview_box = QGroupBox(t("load.group.preview"))
        preview_layout = QVBoxLayout(preview_box)
        self._preview_table = QTableWidget()
        self._preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._preview_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._preview_table.verticalHeader().setDefaultSectionSize(22)
        preview_layout.addWidget(self._preview_table)
        layout.addWidget(preview_box, 1)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        self._open_btn = btns.button(QDialogButtonBox.StandardButton.Open)
        self._open_btn.setEnabled(False)
        layout.addWidget(btns)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("load.dialog.title"),
            "",
            t("load.filter.spreadsheets"),
        )
        if not path:
            return
        self._file_path = path
        self._path_edit.setText(path)
        self._open_btn.setEnabled(True)

        suffix = Path(path).suffix.lower()
        is_xlsx = suffix in {".xlsx", ".xls", ".xlsm"}

        if is_xlsx:
            try:
                self._sheet_names = get_xlsx_sheet_names(path)
            except Exception:
                self._sheet_names = []
            self._sheet_combo.clear()
            self._sheet_combo.addItems(self._sheet_names)
            self._sheet_combo.setVisible(bool(self._sheet_names))
            self._sheet_label.setVisible(bool(self._sheet_names))
            self._delim_label.setVisible(False)
            self._delim_combo.setVisible(False)
        else:
            self._sheet_combo.setVisible(False)
            self._sheet_label.setVisible(False)
            self._delim_label.setVisible(True)
            self._delim_combo.setVisible(True)

        self._refresh_preview()

    def _on_options_changed(self) -> None:
        if self._file_path:
            self._refresh_preview()

    def _refresh_preview(self) -> None:
        if not self._file_path:
            return
        try:
            enc_hint = self._get_encoding_hint()
            delim_hint = self._get_delimiter_hint()
            rows = preview_header_rows(
                self._file_path, n=12, encoding_hint=enc_hint, delimiter_hint=delim_hint
            )
        except Exception as exc:
            self._preview_table.setRowCount(0)
            self._preview_table.setColumnCount(1)
            self._preview_table.setHorizontalHeaderLabels([t("load.preview.error_col")])
            self._preview_table.setItem(0, 0, QTableWidgetItem(str(exc)))
            return

        self._preview_rows = rows
        if not rows:
            self._preview_table.setRowCount(0)
            self._preview_table.setColumnCount(0)
            return

        n_cols = max(len(r) for r in rows)
        self._preview_table.setColumnCount(n_cols)
        self._preview_table.setRowCount(len(rows))

        header_row_idx = self._header_spin.value() - 1  # 0-based

        for r_idx, row in enumerate(rows):
            label = f"{'→ ' if r_idx == header_row_idx else ''}{r_idx + 1}"
            self._preview_table.setVerticalHeaderItem(r_idx, QTableWidgetItem(label))
            for c_idx, cell in enumerate(row):
                item = QTableWidgetItem(cell)
                if r_idx == header_row_idx:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self._preview_table.setItem(r_idx, c_idx, item)

        col_labels = [str(i + 1) for i in range(n_cols)]
        self._preview_table.setHorizontalHeaderLabels(col_labels)
        self._preview_table.resizeColumnsToContents()

    def _get_encoding_hint(self) -> str | None:
        txt = self._encoding_combo.currentText()
        return None if txt == t("load.encoding.auto") else txt

    def _get_delimiter_hint(self) -> str | None:
        txt = self._delim_combo.currentText()
        if txt == t("load.delimiter.auto"):
            return None
        return "\t" if txt == "\\t" else txt

    # ------------------------------------------------------------------
    # Result accessors
    # ------------------------------------------------------------------

    @property
    def file_path(self) -> str | None:
        return self._file_path

    @property
    def header_row(self) -> int:
        """0-based header row index."""
        return self._header_spin.value() - 1

    @property
    def sheet_name(self) -> str | None:
        if self._sheet_combo.isVisible():
            return self._sheet_combo.currentText() or None
        return None

    @property
    def encoding_hint(self) -> str | None:
        return self._get_encoding_hint()

    @property
    def delimiter_hint(self) -> str | None:
        return self._get_delimiter_hint()
