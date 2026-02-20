"""SpreadsheetTableView: custom QTableView."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView


class SpreadsheetTableView(QTableView):
    """Table view with sensible defaults for spreadsheet display."""

    # Emitted when the user right-clicks a column header (logical section index)
    column_context_menu_requested = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        # Selection: click selects row; Ctrl+click for multi
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # Horizontal header: interactive resize + stretch last column
        h_header = self.horizontalHeader()
        h_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        h_header.setStretchLastSection(True)
        h_header.setHighlightSections(False)
        h_header.setDefaultSectionSize(150)
        h_header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        h_header.customContextMenuRequested.connect(self._on_header_right_click)

        # Vertical header: row numbers, fixed width
        v_header = self.verticalHeader()
        v_header.setDefaultSectionSize(28)
        v_header.setFixedWidth(55)
        v_header.setHighlightSections(False)

        # Cosmetic
        self.setShowGrid(True)
        self.setAlternatingRowColors(False)  # we use issue colors instead
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self.setWordWrap(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)

    def _on_header_right_click(self, pos) -> None:
        section = self.horizontalHeader().logicalIndexAt(pos)
        if section >= 0:
            self.column_context_menu_requested.emit(section)

    def scroll_to_cell(self, row: int, col: int) -> None:
        """Scroll to and select a specific cell."""
        if self.model() is None:
            return
        idx = self.model().index(row, col)
        self.setCurrentIndex(idx)
        self.scrollTo(idx, QAbstractItemView.ScrollHint.PositionAtCenter)
