"""ExportController: wires the export dialog to exporters."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from spreadsheet_qa.core.exporters import CSVExporter, IssuesCSVExporter, TXTReporter, XLSXExporter

if TYPE_CHECKING:
    from spreadsheet_qa.core.issue_store import IssueStore
    from spreadsheet_qa.core.models import DatasetMeta
    from spreadsheet_qa.ui.signals import AppSignals
    from spreadsheet_qa.ui.table.table_model import SpreadsheetTableModel


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M")


class ExportController:
    """Handles export to XLSX, CSV, TXT report, and issues.csv."""

    def __init__(
        self,
        table_model: "SpreadsheetTableModel",
        issue_store: "IssueStore",
        signals: "AppSignals",
        parent_widget: QWidget,
    ) -> None:
        self._table_model = table_model
        self._issue_store = issue_store
        self._signals = signals
        self._parent = parent_widget
        self._meta: "DatasetMeta | None" = None

        signals.dataset_loaded.connect(lambda m: setattr(self, "_meta", m))

    def export_xlsx(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self._parent, "Export XLSX", f"cleaned_{_stamp()}.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            XLSXExporter().export(self._table_model.df, Path(path))
            self._signals.status_message.emit(f"Exported XLSX: {path}")
        except Exception as exc:
            QMessageBox.critical(self._parent, "Export error", str(exc))

    def export_csv(self, bom: bool = False) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self._parent, "Export CSV (;)", f"cleaned_{_stamp()}.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            CSVExporter().export(self._table_model.df, Path(path), bom=bom)
            self._signals.status_message.emit(f"Exported CSV: {path}")
        except Exception as exc:
            QMessageBox.critical(self._parent, "Export error", str(exc))

    def export_report(self, output_dir: Path | None = None) -> None:
        if output_dir is None:
            folder = QFileDialog.getExistingDirectory(
                self._parent, "Select export folder"
            )
            if not folder:
                return
            output_dir = Path(folder)

        stamp = _stamp()
        issues = self._issue_store.all_issues()

        try:
            TXTReporter().export(
                issues, output_dir / f"report_{stamp}.txt", meta=self._meta
            )
            IssuesCSVExporter().export(
                issues, output_dir / f"issues_{stamp}.csv", meta=self._meta
            )
            self._signals.status_message.emit(
                f"Exported report + issues.csv to {output_dir}"
            )
        except Exception as exc:
            QMessageBox.critical(self._parent, "Export error", str(exc))

    def export_all(self, output_dir: Path | None = None) -> None:
        """Export XLSX + CSV + TXT + issues.csv to a single folder."""
        if output_dir is None:
            folder = QFileDialog.getExistingDirectory(
                self._parent, "Select export folder"
            )
            if not folder:
                return
            output_dir = Path(folder)

        stamp = _stamp()
        df = self._table_model.df
        issues = self._issue_store.all_issues()

        try:
            XLSXExporter().export(df, output_dir / f"cleaned_{stamp}.xlsx")
            CSVExporter().export(df, output_dir / f"cleaned_{stamp}.csv")
            TXTReporter().export(issues, output_dir / f"report_{stamp}.txt", meta=self._meta)
            IssuesCSVExporter().export(issues, output_dir / f"issues_{stamp}.csv", meta=self._meta)
            self._signals.status_message.emit(f"All exports saved to {output_dir}")
        except Exception as exc:
            QMessageBox.critical(self._parent, "Export error", str(exc))
