"""FindFixDrawer: bottom collapsible drawer for search-and-fix operations."""

from __future__ import annotations

import re
import unicodedata
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
from spreadsheet_qa.ui.i18n import t

if TYPE_CHECKING:
    import pandas as pd

    from spreadsheet_qa.core.issue_store import IssueStore
    from spreadsheet_qa.ui.signals import AppSignals

# Fix type indices (keep in sync with the combo addItems list)
_FIX_EXACT_REPLACE = 0
_FIX_TRIM = 1
_FIX_COLLAPSE = 2
_FIX_UNICODE = 3
_FIX_INVISIBLE = 4
_FIX_NBSP = 5
_FIX_NEWLINES = 6


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
        controls = QGroupBox(t("findfix.title"))
        ctrl_layout = QVBoxLayout(controls)
        ctrl_layout.setSpacing(6)

        form = QFormLayout()
        form.setSpacing(4)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(t("findfix.search.placeholder"))
        self._search_edit.returnPressed.connect(self._find)
        form.addRow(t("findfix.search.label"), self._search_edit)

        self._replace_edit = QLineEdit()
        self._replace_edit.setPlaceholderText(t("findfix.replace.placeholder"))
        form.addRow(t("findfix.replace.label"), self._replace_edit)

        # Fix type selector
        self._fix_type = QComboBox()
        self._fix_type.addItems([
            t("findfix.fixtype.exact_replace"),
            t("findfix.fixtype.trim_whitespace"),
            t("findfix.fixtype.collapse_spaces"),
            t("findfix.fixtype.normalize_unicode"),
            t("findfix.fixtype.strip_invisible"),
            t("findfix.fixtype.replace_nbsp"),
            t("findfix.fixtype.normalize_newlines"),
        ])
        self._fix_type.currentIndexChanged.connect(self._on_fix_type_changed)
        form.addRow(t("findfix.fixtype.label"), self._fix_type)

        # Column filter
        self._col_filter = QComboBox()
        self._col_filter.addItem(t("findfix.col.all"))
        form.addRow(t("findfix.col.label"), self._col_filter)

        ctrl_layout.addLayout(form)

        btn_row = QHBoxLayout()
        self._find_btn = QPushButton(t("findfix.btn.find"))
        self._find_btn.clicked.connect(self._find)
        self._apply_btn = QPushButton(t("findfix.btn.apply_selected"))
        self._apply_btn.clicked.connect(self._apply_selected)
        self._apply_btn.setEnabled(False)
        self._apply_all_btn = QPushButton(t("findfix.btn.apply_all"))
        self._apply_all_btn.clicked.connect(self._apply_all)
        self._apply_all_btn.setEnabled(False)
        btn_row.addWidget(self._find_btn)
        btn_row.addWidget(self._apply_btn)
        btn_row.addWidget(self._apply_all_btn)
        ctrl_layout.addLayout(btn_row)
        layout.addWidget(controls, 1)

        # Right: matches preview
        preview = QGroupBox(t("findfix.preview.title"))
        prev_layout = QVBoxLayout(preview)
        self._match_count_label = QLabel(t("findfix.preview.empty"))
        prev_layout.addWidget(self._match_count_label)
        self._matches_list = QListWidget()
        self._matches_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        prev_layout.addWidget(self._matches_list)
        layout.addWidget(preview, 2)

    def _on_fix_type_changed(self, idx: int) -> None:
        show_replace = idx == _FIX_EXACT_REPLACE
        self._replace_edit.setEnabled(show_replace)
        self._search_edit.setEnabled(idx == _FIX_EXACT_REPLACE)

    def set_dataframe(self, df: "pd.DataFrame") -> None:
        self._df = df
        self._col_filter.clear()
        self._col_filter.addItem(t("findfix.col.all"))
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

        all_cols_label = t("findfix.col.all")
        cols = (
            list(self._df.columns)
            if col_filter == all_cols_label
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
                        t(
                            "findfix.preview.item",
                            row=row_idx + 1,
                            col=col,
                            old=repr(s),
                            new=repr(new_val),
                        )
                    )
                    self._matches_list.addItem(item)

        count = len(self._matches)
        self._match_count_label.setText(
            t("findfix.preview.count", n=count) if count else t("findfix.preview.none")
        )
        self._apply_all_btn.setEnabled(count > 0)
        self._apply_btn.setEnabled(count > 0)

    def _compute_fix(
        self, fix_type: int, value: str, search: str, replace: str
    ) -> str | None:
        """Return the fixed value or None if no fix applies."""
        if fix_type == _FIX_EXACT_REPLACE:
            if search and search in value:
                return value.replace(search, replace)
            return None
        elif fix_type == _FIX_TRIM:
            stripped = value.strip()
            return stripped if stripped != value else None
        elif fix_type == _FIX_COLLAPSE:
            collapsed = re.sub(r"  +", " ", value).strip()
            return collapsed if collapsed != value else None
        elif fix_type == _FIX_UNICODE:
            fixed = value
            for ch, rep in _UNICODE_SUSPECTS.items():
                fixed = fixed.replace(ch, rep)
            # NFC normalisation
            fixed = unicodedata.normalize("NFC", fixed)
            return fixed if fixed != value else None
        elif fix_type == _FIX_INVISIBLE:
            fixed = _INVISIBLE_RE.sub("", value)
            return fixed if fixed != value else None
        elif fix_type == _FIX_NBSP:
            fixed = value.replace("\u00a0", " ")
            return fixed if fixed != value else None
        elif fix_type == _FIX_NEWLINES:
            fixed = value.replace("\r\n", "\n").replace("\r", "\n")
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
        self._matches = []
        self._matches_list.clear()
        self._match_count_label.setText(t("findfix.applied"))
        self._apply_all_btn.setEnabled(False)
        self._apply_btn.setEnabled(False)
