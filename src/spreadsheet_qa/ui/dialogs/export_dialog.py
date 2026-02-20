"""ExportDialog: choose export formats and destination."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ExportDialog(QDialog):
    """Let the user pick formats and output directory for export."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export")
        self.setMinimumWidth(450)
        self._output_dir: Path | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Output folder
        folder_box = QGroupBox("Output folder")
        folder_layout = QHBoxLayout(folder_box)
        self._folder_edit = QLineEdit()
        self._folder_edit.setReadOnly(True)
        self._folder_edit.setPlaceholderText("Select a folder…")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        folder_layout.addWidget(self._folder_edit, 1)
        folder_layout.addWidget(browse_btn)
        layout.addWidget(folder_box)

        # Format choices
        fmt_box = QGroupBox("Formats")
        fmt_layout = QVBoxLayout(fmt_box)
        self._xlsx_check = QCheckBox("Cleaned spreadsheet (XLSX)")
        self._xlsx_check.setChecked(True)
        self._csv_check = QCheckBox("Cleaned spreadsheet (CSV  —  delimiter: ;)")
        self._csv_check.setChecked(True)
        self._csv_bom_check = QCheckBox("  UTF-8 BOM (for Excel on Windows)")
        self._csv_bom_check.setEnabled(True)
        self._report_check = QCheckBox("Validation report (TXT)")
        self._report_check.setChecked(True)
        self._issues_csv_check = QCheckBox("Issues list (CSV  —  delimiter: ;)")
        self._issues_csv_check.setChecked(True)
        fmt_layout.addWidget(self._xlsx_check)
        fmt_layout.addWidget(self._csv_check)
        fmt_layout.addWidget(self._csv_bom_check)
        fmt_layout.addWidget(self._report_check)
        fmt_layout.addWidget(self._issues_csv_check)
        layout.addWidget(fmt_box)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select export folder")
        if folder:
            self._folder_edit.setText(folder)
            self._output_dir = Path(folder)

    @property
    def output_dir(self) -> Path | None:
        return self._output_dir

    @property
    def export_xlsx(self) -> bool:
        return self._xlsx_check.isChecked()

    @property
    def export_csv(self) -> bool:
        return self._csv_check.isChecked()

    @property
    def csv_bom(self) -> bool:
        return self._csv_bom_check.isChecked()

    @property
    def export_report(self) -> bool:
        return self._report_check.isChecked()

    @property
    def export_issues_csv(self) -> bool:
        return self._issues_csv_check.isChecked()
