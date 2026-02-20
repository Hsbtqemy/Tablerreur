"""IssueStore: in-memory collection of Issue objects.

Provides O(1) lookup by (row, col) for cell painting, and O(1) replacement
by column for incremental re-validation.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Iterable

from spreadsheet_qa.core.models import Issue, IssueStatus, Severity


class IssueStore:
    """Thread-unsafe in-memory store for Issue objects.

    Must only be accessed from the main (Qt) thread.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, Issue] = {}
        # secondary indexes
        self._by_col: dict[str, list[str]] = defaultdict(list)  # col → [issue_id]
        self._by_cell: dict[tuple[int, str], list[str]] = defaultdict(list)  # (row,col) → [ids]

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def replace_all(self, issues: Iterable[Issue]) -> None:
        """Replace the entire store with a new set of issues."""
        self._by_id.clear()
        self._by_col.clear()
        self._by_cell.clear()
        for issue in issues:
            self._insert(issue)

    def replace_for_columns(self, cols: list[str], issues: Iterable[Issue]) -> None:
        """Replace issues for specific columns only; leave other columns intact."""
        # Remove existing issues for those columns
        for col in cols:
            for issue_id in self._by_col.get(col, []):
                issue = self._by_id.pop(issue_id, None)
                if issue is not None:
                    cell_key = (issue.row, issue.col)
                    cell_list = self._by_cell.get(cell_key)
                    if cell_list is not None and issue_id in cell_list:
                        cell_list.remove(issue_id)
                        if not cell_list:
                            del self._by_cell[cell_key]
            self._by_col[col] = []

        # Insert new issues
        for issue in issues:
            if issue.col in cols or issue.col == "__row__":
                self._insert(issue)

    def set_status(self, issue_id: str, status: IssueStatus) -> None:
        issue = self._by_id.get(issue_id)
        if issue is not None:
            issue.status = status

    def _insert(self, issue: Issue) -> None:
        self._by_id[issue.id] = issue
        self._by_col[issue.col].append(issue.id)
        self._by_cell[(issue.row, issue.col)].append(issue.id)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def by_cell(self, row: int, col: str) -> list[Issue]:
        """Return all issues for a specific cell. O(k) where k is count."""
        ids = self._by_cell.get((row, col), [])
        return [self._by_id[i] for i in ids if i in self._by_id]

    def by_column(self, col: str) -> list[Issue]:
        ids = self._by_col.get(col, [])
        return [self._by_id[i] for i in ids if i in self._by_id]

    def get(self, issue_id: str) -> Issue | None:
        return self._by_id.get(issue_id)

    def all_issues(self) -> list[Issue]:
        return list(self._by_id.values())

    def open_issues(self) -> list[Issue]:
        return [i for i in self._by_id.values() if i.status == IssueStatus.OPEN]

    def count_by_severity(self) -> dict[Severity, int]:
        counts: dict[Severity, int] = {s: 0 for s in Severity}
        for issue in self._by_id.values():
            if issue.status == IssueStatus.OPEN:
                counts[issue.severity] += 1
        return counts

    def has_issues_for_cell(self, row: int, col: str) -> bool:
        return bool(self._by_cell.get((row, col)))

    def worst_severity_for_cell(self, row: int, col: str) -> Severity | None:
        issues = self.by_cell(row, col)
        open_issues = [i for i in issues if i.status == IssueStatus.OPEN]
        if not open_issues:
            return None
        return min(i.severity for i in open_issues)

    def __len__(self) -> int:
        return len(self._by_id)
