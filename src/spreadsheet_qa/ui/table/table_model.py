"""SpreadsheetTableModel: QAbstractTableModel backed by a pandas DataFrame.

Critical design rules:
- Holds a DIRECT REFERENCE to the DataFrame — no copies.
- setData() does NOT mutate df directly; emits cell_edit_requested signal.
- data() accesses df.iloc for O(1) cell lookup.
- Background color computed from IssueStore on BackgroundRole.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from spreadsheet_qa.core.models import Severity
from spreadsheet_qa.ui.signals import AppSignals

# Severity → subtle background color
_SEVERITY_COLORS = {
    Severity.ERROR: QColor(255, 220, 220),       # soft red
    Severity.WARNING: QColor(255, 243, 200),     # soft amber
    Severity.SUSPICION: QColor(230, 230, 255),   # soft blue/lavender
}


class SpreadsheetTableModel(QAbstractTableModel):
    """Thin Qt model wrapping a pandas DataFrame.

    The model does not own the DataFrame or the IssueStore.
    It reads from them on every paint event (Qt handles virtualization).
    """

    def __init__(self, df: pd.DataFrame, issue_store: Any, signals: AppSignals, parent=None) -> None:
        super().__init__(parent)
        self._df = df
        self._issue_store = issue_store
        self._signals = signals

    # ------------------------------------------------------------------
    # Qt required overrides
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._df)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._df.columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row, col_idx = index.row(), index.column()

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            val = self._df.iloc[row, col_idx]
            if pd.isna(val):
                return ""
            return str(val)

        if role == Qt.ItemDataRole.UserRole:
            return self._df.iloc[row, col_idx]

        if role == Qt.ItemDataRole.BackgroundRole:
            col_name = self._df.columns[col_idx]
            severity = self._issue_store.worst_severity_for_cell(row, col_name)
            if severity is not None:
                return _SEVERITY_COLORS.get(severity)

        if role == Qt.ItemDataRole.ToolTipRole:
            col_name = self._df.columns[col_idx]
            issues = self._issue_store.by_cell(row, col_name)
            if issues:
                return "\n".join(i.message for i in issues[:5])

        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._df.columns[section]
        return str(section + 1)  # 1-based row numbers

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """Route edit requests through the FixController via signal."""
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
        row = index.row()
        col_name = self._df.columns[index.column()]
        # Emit signal to FixController — do NOT mutate df here
        self._signals.cell_edit_requested.emit(row, col_name, value)
        return False  # Qt should not set data directly

    # ------------------------------------------------------------------
    # Model refresh helpers
    # ------------------------------------------------------------------

    def refresh_cell(self, row: int, col_idx: int) -> None:
        """Notify Qt that a single cell has changed."""
        idx = self.index(row, col_idx)
        self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.BackgroundRole])

    def refresh_all(self) -> None:
        """Notify Qt that all data has changed (after full validation update)."""
        # Guard: do not emit dataChanged for invalid indexes on empty tables.
        if self.rowCount() == 0 or self.columnCount() == 0:
            return
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1),
            [Qt.ItemDataRole.BackgroundRole],
        )

    def replace_dataframe(self, df: pd.DataFrame) -> None:
        """Swap the underlying DataFrame (e.g., after file reload)."""
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def column_names(self) -> list[str]:
        return list(self._df.columns)
