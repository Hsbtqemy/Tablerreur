"""ValidationController: runs ValidationEngine in a QThread worker."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from spreadsheet_qa.core.engine import ValidationEngine
from spreadsheet_qa.core.models import Issue
from spreadsheet_qa.ui.i18n import t

if TYPE_CHECKING:
    import pandas as pd

    from spreadsheet_qa.core.issue_store import IssueStore
    from spreadsheet_qa.ui.signals import AppSignals


class _ValidationWorker(QRunnable):
    class _Signals(QObject):
        finished = Signal(list)  # list[Issue]

    def __init__(self, df, columns, config) -> None:
        super().__init__()
        self.df = df
        self.columns = columns
        self.config = config
        self.signals = self._Signals()

    def run(self) -> None:
        engine = ValidationEngine()
        issues = engine.validate(self.df, self.columns, self.config)
        self.signals.finished.emit(issues)


class ValidationController:
    """Manages running validation asynchronously and feeding IssueStore."""

    def __init__(
        self,
        table_model,
        issue_store: "IssueStore",
        signals: "AppSignals",
    ) -> None:
        self._table_model = table_model
        self._issue_store = issue_store
        self._signals = signals
        self._config: dict = {}
        self._thread_pool = QThreadPool.globalInstance()

        self._signals.dataset_loaded.connect(self._on_dataset_loaded)

    def set_config(self, config: dict) -> None:
        self._config = config

    def set_column_override(self, col: str, overrides: dict) -> None:
        """Merge *overrides* into the in-memory column config and re-validate that column."""
        columns_cfg = self._config.setdefault("columns", {})
        col_cfg = dict(columns_cfg.get(col, {}))
        col_cfg.update(overrides)
        columns_cfg[col] = col_cfg
        self.run_partial([col])

    @Slot()
    def _on_dataset_loaded(self, meta) -> None:
        self.run_full()

    def run_full(self) -> None:
        """Validate all columns. Replaces all issues."""
        df = self._table_model.df
        if df is None or df.empty:
            return
        self._signals.validation_started.emit()
        self._run(df.copy(), columns=None, replace_cols=None)

    def run_partial(self, columns: list[str]) -> None:
        """Validate only the given columns. Leaves other columns' issues intact."""
        df = self._table_model.df
        if df is None or df.empty:
            return
        self._run(df.copy(), columns=columns, replace_cols=columns)

    def _run(self, df, columns, replace_cols) -> None:
        worker = _ValidationWorker(df, columns, self._config)
        worker.signals.finished.connect(lambda issues: self._on_finished(issues, replace_cols))
        self._thread_pool.start(worker)

    def _on_finished(self, issues: list[Issue], replace_cols: list[str] | None) -> None:
        if replace_cols is None:
            self._issue_store.replace_all(issues)
        else:
            self._issue_store.replace_for_columns(replace_cols, issues)

        self._signals.issues_updated.emit()
        self._table_model.refresh_all()
        self._signals.validation_finished.emit(len(self._issue_store))

        counts = self._issue_store.count_by_severity()
        from spreadsheet_qa.core.models import Severity
        e = counts.get(Severity.ERROR, 0)
        w = counts.get(Severity.WARNING, 0)
        s = counts.get(Severity.SUSPICION, 0)
        self._signals.status_message.emit(
            t("status.validation_done", e=e, w=w, s=s)
        )
