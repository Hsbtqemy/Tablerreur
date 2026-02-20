"""IssuesPanel: filterable list of validation issues."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtGui import QBrush, QColor, QPalette, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from spreadsheet_qa.core.models import Issue, IssueStatus, Severity
from spreadsheet_qa.ui.i18n import severity_label, status_label, t

if TYPE_CHECKING:
    from spreadsheet_qa.core.issue_store import IssueStore
    from spreadsheet_qa.ui.signals import AppSignals


_COL_SEVERITY = 0
_COL_STATUS = 1
_COL_COLUMN = 2
_COL_ROW = 3
_COL_MESSAGE = 4
_COL_SUGGESTION = 5

_SEVERITY_COLORS_LIGHT = {
    Severity.ERROR: QColor(180, 0, 0),
    Severity.WARNING: QColor(150, 90, 0),
    Severity.SUSPICION: QColor(60, 60, 180),
}
_SEVERITY_COLORS_DARK = {
    Severity.ERROR: QColor(255, 100, 100),
    Severity.WARNING: QColor(255, 200, 60),
    Severity.SUSPICION: QColor(130, 130, 255),
}


def _severity_fg_color(severity: Severity) -> QColor:
    """Return a severity foreground color adapted to the current light/dark theme."""
    app = QApplication.instance()
    if app is not None:
        bg = app.palette().color(QPalette.ColorRole.Window)
        if bg.value() < 128:  # HSV value — dark background
            return _SEVERITY_COLORS_DARK.get(severity, QColor(220, 220, 220))
    return _SEVERITY_COLORS_LIGHT.get(severity, QColor(80, 80, 80))


class IssuesPanel(QWidget):
    """Displays validation issues with filtering and jump-to-cell."""

    def __init__(
        self, issue_store: "IssueStore", signals: "AppSignals", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._issue_store = issue_store
        self._signals = signals
        self._source_model = QStandardItemModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._source_model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(6)

        self._sev_combo = QComboBox()
        self._sev_combo.addItems([
            t("severity.all"),
            severity_label("ERROR"),
            severity_label("WARNING"),
            severity_label("SUSPICION"),
        ])
        self._sev_combo.currentIndexChanged.connect(self._apply_filters)

        self._status_combo = QComboBox()
        self._status_combo.addItems([
            t("status.open_only"),
            t("status.all"),
            status_label("FIXED"),
            status_label("IGNORED"),
        ])
        self._status_combo.currentIndexChanged.connect(self._apply_filters)

        self._col_combo = QComboBox()
        self._col_combo.addItem(t("issues.filter.all_cols"))
        self._col_combo.currentIndexChanged.connect(self._apply_filters)

        self._count_label = QLabel(t("issues.count", n=0))

        filter_bar.addWidget(QLabel(t("issues.filter.severity")))
        filter_bar.addWidget(self._sev_combo)
        filter_bar.addWidget(QLabel(t("issues.filter.status")))
        filter_bar.addWidget(self._status_combo)
        filter_bar.addWidget(QLabel(t("issues.filter.column")))
        filter_bar.addWidget(self._col_combo)
        filter_bar.addStretch()
        filter_bar.addWidget(self._count_label)
        layout.addLayout(filter_bar)

        # Tree view
        self._tree = QTreeView()
        self._tree.setModel(self._proxy)
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self._tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self._tree.doubleClicked.connect(self._on_double_click)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)

        # Setup columns
        self._source_model.setHorizontalHeaderLabels([
            t("issues.col.severity"),
            t("issues.col.status"),
            t("issues.col.column"),
            t("issues.col.row"),
            t("issues.col.message"),
            t("issues.col.suggestion"),
        ])
        header = self._tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.resizeSection(0, 60)
        header.resizeSection(1, 80)
        header.resizeSection(2, 120)
        header.resizeSection(3, 55)
        header.resizeSection(4, 300)
        header.resizeSection(5, 200)
        self._tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        layout.addWidget(self._tree, 1)

    def _connect_signals(self) -> None:
        self._signals.issues_updated.connect(self.refresh)
        self._signals.patch_applied.connect(lambda _: self.refresh())
        self._signals.patch_undone.connect(lambda _: self.refresh())

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Rebuild the model from the issue store."""
        self._source_model.removeRows(0, self._source_model.rowCount())

        # Collect all columns for filter combo
        all_issues = self._issue_store.all_issues()
        cols = sorted({i.col for i in all_issues if i.col != "__row__"})

        current_col = self._col_combo.currentText()
        self._col_combo.blockSignals(True)
        self._col_combo.clear()
        self._col_combo.addItem(t("issues.filter.all_cols"))
        for col in cols:
            self._col_combo.addItem(col)
        idx = self._col_combo.findText(current_col)
        if idx >= 0:
            self._col_combo.setCurrentIndex(idx)
        self._col_combo.blockSignals(False)

        for issue in all_issues:
            row_items = [
                QStandardItem(severity_label(issue.severity.value)),
                QStandardItem(status_label(issue.status.value)),
                QStandardItem(issue.col if issue.col != "__row__" else t("issues.row_label")),
                QStandardItem(str(issue.row + 1)),
                QStandardItem(issue.message),
                QStandardItem(str(issue.suggestion) if issue.suggestion is not None else ""),
            ]
            # Colour severity column (adapts to light/dark theme)
            row_items[0].setForeground(QBrush(_severity_fg_color(issue.severity)))
            row_items[0].setFont(row_items[0].font())

            # Store issue id for retrieval
            row_items[0].setData(issue.id, Qt.ItemDataRole.UserRole)
            # Store original severity/status values for filtering
            row_items[0].setData(issue.severity.value, Qt.ItemDataRole.UserRole + 1)
            row_items[1].setData(issue.status.value, Qt.ItemDataRole.UserRole + 1)

            self._source_model.appendRow(row_items)

        self._apply_filters()

    def _apply_filters(self) -> None:
        sev_text = self._sev_combo.currentText()
        status_text = self._status_combo.currentText()
        col_text = self._col_combo.currentText()

        all_sevs_label = t("severity.all")
        all_status_label = t("status.all")
        open_only_label = t("status.open_only")
        all_cols_label = t("issues.filter.all_cols")
        open_internal = "OPEN"

        visible = 0
        for row in range(self._source_model.rowCount()):
            sev_item = self._source_model.item(row, _COL_SEVERITY)
            status_item = self._source_model.item(row, _COL_STATUS)
            col_item = self._source_model.item(row, _COL_COLUMN)

            # Use original enum values stored as UserRole+1 for reliable filtering
            sev_val = sev_item.data(Qt.ItemDataRole.UserRole + 1) if sev_item else ""
            status_val = status_item.data(Qt.ItemDataRole.UserRole + 1) if status_item else ""
            col_val = col_item.text() if col_item else ""

            show = True
            if sev_text != all_sevs_label and severity_label(sev_val) != sev_text:
                show = False
            if status_text == open_only_label and status_val != open_internal:
                show = False
            elif status_text not in (open_only_label, all_status_label):
                # Comparing French display labels
                if status_label(status_val) != status_text:
                    show = False
            if col_text != all_cols_label and col_val != col_text:
                show = False

            idx = self._source_model.index(row, 0)
            proxy_idx = self._proxy.mapFromSource(idx)
            self._tree.setRowHidden(proxy_idx.row(), proxy_idx.parent(), not show)
            if show:
                visible += 1

        self._count_label.setText(t("issues.count", n=visible))

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_double_click(self, proxy_index) -> None:
        src_index = self._proxy.mapToSource(proxy_index)
        issue_id = self._source_model.item(src_index.row(), 0).data(Qt.ItemDataRole.UserRole)
        issue = self._issue_store.get(issue_id)
        if issue:
            self._signals.issue_selected.emit(issue)

    def _show_context_menu(self, pos) -> None:
        proxy_index = self._tree.indexAt(pos)
        if not proxy_index.isValid():
            return
        src_index = self._proxy.mapToSource(proxy_index)
        issue_id = self._source_model.item(src_index.row(), 0).data(Qt.ItemDataRole.UserRole)
        issue = self._issue_store.get(issue_id)
        if not issue:
            return

        menu = QMenu(self)
        go_act = menu.addAction(t("issues.ctx.goto"))
        ignore_act = menu.addAction(t("issues.ctx.ignore"))
        except_act = menu.addAction(t("issues.ctx.except"))

        action = menu.exec(self._tree.mapToGlobal(pos))
        if action == go_act:
            self._signals.issue_selected.emit(issue)
        elif action == ignore_act:
            self._issue_store.set_status(issue.id, IssueStatus.IGNORED)
            self._signals.issue_status_changed.emit(issue.id, IssueStatus.IGNORED.value)
            self.refresh()
        elif action == except_act:
            self._issue_store.set_status(issue.id, IssueStatus.EXCEPTED)
            self._signals.issue_status_changed.emit(issue.id, IssueStatus.EXCEPTED.value)
            self.refresh()
