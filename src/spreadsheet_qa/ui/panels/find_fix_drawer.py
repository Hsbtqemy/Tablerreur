"""FindFixDrawer: bottom collapsible drawer for search-and-fix operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from spreadsheet_qa.core.text_utils import INVISIBLE_RE as _INVISIBLE_RE
from spreadsheet_qa.core.text_utils import UNICODE_SUSPECTS as _UNICODE_SUSPECTS

if TYPE_CHECKING:
    import pandas as pd

    from spreadsheet_qa.core.issue_store import IssueStore
    from spreadsheet_qa.ui.signals import AppSignals


class FindFixDrawer(QWidget):
    """Search-and-fix panel (typically docked at the bottom)."""

    def __init__(
        self,
        issue_store: "IssueStore",
        signals: "AppSignals",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._issue_store = issue_store
        self._signals = signals
        self._df = None  # set by controller after load
        self._fix_controller = None  # set by controller
        self._matches: list[tuple[int, str, Any, Any]] = []  # (row, col, old, new)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # Left: search / fix controls
        controls = QGroupBox("Find & Fix")
        ctrl_layout = QVBoxLayout(controls)
        ctrl_layout.setSpacing(6)

        form = QFormLayout()
        form.setSpacing(4)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search value…")
        self._search_edit.returnPressed.connect(self._find)
        form.addRow("Find:", self._search_edit)

        self._replace_edit = QLineEdit()
        self._replace_edit.setPlaceholderText("Replace with…")
        form.addRow("Replace:", self._replace_edit)

        # Fix type selector
        self._fix_type = QComboBox()
        self._fix_type.addItems([
            "Replace exact match",
            "Trim whitespace",
            "Collapse spaces",
            "Normalize unicode",
            "Strip invisible chars",
        ])
        self._fix_type.currentIndexChanged.connect(self._on_fix_type_changed)
        form.addRow("Fix type:", self._fix_type)

        # Column filter
        self._col_filter = QComboBox()
        self._col_filter.addItem("All columns")
        form.addRow("In column:", self._col_filter)

        ctrl_layout.addLayout(form)

        btn_row = QHBoxLayout()
        self._find_btn = QPushButton("Find")
        self._find_btn.clicked.connect(self._find)
        self._apply_btn = QPushButton("Apply selected")
        self._apply_btn.clicked.connect(self._apply_selected)
        self._apply_btn.setEnabled(False)
        self._apply_all_btn = QPushButton("Apply all")
        self._apply_all_btn.clicked.connect(self._apply_all)
        self._apply_all_btn.setEnabled(False)
        btn_row.addWidget(self._find_btn)
        btn_row.addWidget(self._apply_btn)
        btn_row.addWidget(self._apply_all_btn)
        ctrl_layout.addLayout(btn_row)
        layout.addWidget(controls, 1)

        # Right: matches preview
        preview = QGroupBox("Matches preview")
        prev_layout = QVBoxLayout(preview)
        self._match_count_label = QLabel("No search performed.")
        prev_layout.addWidget(self._match_count_label)
        self._matches_list = QListWidget()
        self._matches_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        prev_layout.addWidget(self._matches_list)
        layout.addWidget(preview, 2)

    def _on_fix_type_changed(self, idx: int) -> None:
        show_replace = idx == 0  # "Replace exact match"
        self._replace_edit.setEnabled(show_replace)
        self._search_edit.setEnabled(idx in (0,))  # only for replace

    def set_dataframe(self, df: "pd.DataFrame") -> None:
        self._df = df
        # Refresh column list
        self._col_filter.clear()
        self._col_filter.addItem("All columns")
        for col in df.columns:
            self._col_filter.addItem(col)

    def set_fix_controller(self, controller) -> None:
        self._fix_controller = controller

    def _find(self) -> None:
        if self._df is None:
            return

        import pandas as pd

        self._matches = []
        self._matches_list.clear()

        fix_type = self._fix_type.currentIndex()
        col_filter = self._col_filter.currentText()
        search_term = self._search_edit.text()
        replace_with = self._replace_edit.text()

        cols = (
            list(self._df.columns)
            if col_filter == "All columns"
            else [col_filter]
        )

        for col in cols:
            if col not in self._df.columns:
                continue
            for row_idx, val in self._df[col].items():
                if pd.isna(val):
                    continue
                s = str(val)
                new_val = self._compute_fix(fix_type, s, search_term, replace_with)
                if new_val is not None and new_val != s:
                    self._matches.append((int(row_idx), col, s, new_val))
                    item = QListWidgetItem(
                        f"Row {row_idx + 1} | {col}: {s!r} → {new_val!r}"
                    )
                    self._matches_list.addItem(item)

        count = len(self._matches)
        self._match_count_label.setText(
            f"{count} match(es)" if count else "No matches found."
        )
        self._apply_all_btn.setEnabled(count > 0)
        self._apply_btn.setEnabled(count > 0)

    def _compute_fix(
        self, fix_type: int, value: str, search: str, replace: str
    ) -> str | None:
        """Return the fixed value or None if no fix applies."""
        import re

        if fix_type == 0:  # exact replace
            if search and search in value:
                return value.replace(search, replace)
            return None
        elif fix_type == 1:  # trim whitespace
            stripped = value.strip()
            return stripped if stripped != value else None
        elif fix_type == 2:  # collapse spaces
            collapsed = re.sub(r"  +", " ", value).strip()
            return collapsed if collapsed != value else None
        elif fix_type == 3:  # normalize unicode
            fixed = value
            for ch, rep in _UNICODE_SUSPECTS.items():
                fixed = fixed.replace(ch, rep)
            return fixed if fixed != value else None
        elif fix_type == 4:  # strip invisible
            fixed = _INVISIBLE_RE.sub("", value)
            return fixed if fixed != value else None
        return None

    def _apply_selected(self) -> None:
        selected_rows = {self._matches_list.row(item) for item in self._matches_list.selectedItems()}
        to_apply = [m for i, m in enumerate(self._matches) if i in selected_rows]
        self._apply_matches(to_apply)

    def _apply_all(self) -> None:
        self._apply_matches(self._matches)

    def _apply_matches(self, matches: list) -> None:
        if not matches or self._fix_controller is None:
            return
        self._fix_controller.apply_bulk(matches)
        # Clear after apply
        self._matches = []
        self._matches_list.clear()
        self._match_count_label.setText("Applied. Run Find again to check remaining issues.")
        self._apply_all_btn.setEnabled(False)
        self._apply_btn.setEnabled(False)
