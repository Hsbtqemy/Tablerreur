"""ExportController: wires the export dialog to exporters."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from spreadsheet_qa.core.exporters import CSVExporter, IssuesCSVExporter, TXTReporter, XLSXExporter
from spreadsheet_qa.ui.i18n import t

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
            self._parent,
            t("export.title"),
            f"nettoyé_{_stamp()}.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return
        try:
            XLSXExporter().export(self._table_model.df, Path(path))
            self._signals.status_message.emit(t("status.export_done", path=path))
        except Exception as exc:
            QMessageBox.critical(self._parent, t("export.error_title"), str(exc))

    def export_csv(self, bom: bool = False) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self._parent,
            t("export.title"),
            f"nettoyé_{_stamp()}.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            CSVExporter().export(self._table_model.df, Path(path), bom=bom)
            self._signals.status_message.emit(t("status.export_done", path=path))
        except Exception as exc:
            QMessageBox.critical(self._parent, t("export.error_title"), str(exc))

    def export_report(self, output_dir: Path | None = None) -> None:
        if output_dir is None:
            folder = QFileDialog.getExistingDirectory(
                self._parent, t("export.dialog.folder")
            )
            if not folder:
                return
            output_dir = Path(folder)

        stamp = _stamp()
        issues = self._issue_store.all_issues()

        try:
            TXTReporter().export(
                issues, output_dir / f"rapport_{stamp}.txt", meta=self._meta
            )
            IssuesCSVExporter().export(
                issues, output_dir / f"problèmes_{stamp}.csv", meta=self._meta
            )
            self._signals.status_message.emit(t("status.export_done", path=output_dir))
        except Exception as exc:
            QMessageBox.critical(self._parent, t("export.error_title"), str(exc))

    def export_all(self, output_dir: Path | None = None) -> None:
        """Export XLSX + CSV + TXT + problèmes.csv to a single folder."""
        if output_dir is None:
            folder = QFileDialog.getExistingDirectory(
                self._parent, t("export.dialog.folder")
            )
            if not folder:
                return
            output_dir = Path(folder)

        stamp = _stamp()
        df = self._table_model.df
        issues = self._issue_store.all_issues()

        try:
            XLSXExporter().export(df, output_dir / f"nettoyé_{stamp}.xlsx")
            CSVExporter().export(df, output_dir / f"nettoyé_{stamp}.csv")
            TXTReporter().export(issues, output_dir / f"rapport_{stamp}.txt", meta=self._meta)
            IssuesCSVExporter().export(issues, output_dir / f"problèmes_{stamp}.csv", meta=self._meta)
            self._signals.status_message.emit(t("status.export_done", path=output_dir))
        except Exception as exc:
            QMessageBox.critical(self._parent, t("export.error_title"), str(exc))
