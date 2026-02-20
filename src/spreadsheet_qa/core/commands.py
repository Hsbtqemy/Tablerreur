"""Command pattern for undoable fixes.

All user-visible changes to the DataFrame must go through a Command so that
the undo/redo stack stays consistent.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import pandas as pd

from spreadsheet_qa.core.models import ActionLogEntry, IssueStatus, Patch

if TYPE_CHECKING:
    from spreadsheet_qa.core.issue_store import IssueStore
    from spreadsheet_qa.core.patch import PatchWriter
    from spreadsheet_qa.core.project import ProjectManager


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


class Command(ABC):
    """Abstract base for all undoable commands."""

    @abstractmethod
    def execute(self) -> None: ...

    @abstractmethod
    def undo(self) -> None: ...

    @property
    @abstractmethod
    def description(self) -> str: ...


class ApplyCellFixCommand(Command):
    """Apply a single-cell fix: df.at[row, col] = new_value."""

    def __init__(
        self,
        df: pd.DataFrame,
        row: int,
        col: str,
        old_value: Any,
        new_value: Any,
        issue_store: "IssueStore",
        patch_writer: "PatchWriter",
        project_manager: "ProjectManager | None" = None,
        issue_id: str | None = None,
    ) -> None:
        self._df = df
        self._row = row
        self._col = col
        self._old_value = old_value
        self._new_value = new_value
        self._issue_store = issue_store
        self._patch_writer = patch_writer
        self._project = project_manager
        self._issue_id = issue_id

        self._action_id = str(uuid.uuid4())[:8]
        self._patch: Patch | None = None

    def execute(self) -> None:
        ts = _now_iso()
        self._df.at[self._row, self._col] = self._new_value

        patch_id = f"{self._action_id}_p0"
        self._patch = Patch(
            patch_id=patch_id,
            action_id=self._action_id,
            row=self._row,
            col=self._col,
            old_value=self._old_value,
            new_value=self._new_value,
            issue_id=self._issue_id,
            timestamp=ts,
        )
        self._patch_writer.write(self._patch)

        if self._issue_id:
            self._issue_store.set_status(self._issue_id, IssueStatus.FIXED)

        if self._project:
            entry = ActionLogEntry(
                action_id=self._action_id,
                timestamp=ts,
                action_type="fix",
                scope="cell",
                params={"row": self._row, "col": self._col, "new_value": str(self._new_value)},
                stats={"cells_changed": 1},
                patch_ids=[patch_id],
            )
            self._project.append_action_log(entry)

    def undo(self) -> None:
        self._df.at[self._row, self._col] = self._old_value

        if self._patch:
            self._patch_writer.delete(self._patch.patch_id)

        if self._issue_id:
            self._issue_store.set_status(self._issue_id, IssueStatus.OPEN)

        if self._project and self._patch:
            ts = _now_iso()
            entry = ActionLogEntry(
                action_id=str(uuid.uuid4())[:8],
                timestamp=ts,
                action_type="undo",
                scope="cell",
                params={"original_action_id": self._action_id},
                patch_ids=[self._patch.patch_id],
            )
            self._project.append_action_log(entry)

    @property
    def patch(self) -> "Patch | None":
        return self._patch

    @property
    def description(self) -> str:
        return (
            f"Fix «{self._col}»[{self._row + 1}]: "
            f"{self._old_value!r} → {self._new_value!r}"
        )


class BulkCellFixCommand(Command):
    """Composite command wrapping multiple single-cell fixes."""

    def __init__(self, commands: list[ApplyCellFixCommand], label: str = "Bulk fix") -> None:
        self._commands = commands
        self._label = label

    def execute(self) -> None:
        for cmd in self._commands:
            cmd.execute()

    def undo(self) -> None:
        for cmd in reversed(self._commands):
            cmd.undo()

    @property
    def description(self) -> str:
        return f"{self._label} ({len(self._commands)} cells)"


class SetIssueStatusCommand(Command):
    """Change issue status (IGNORED / EXCEPTED) — also undoable."""

    def __init__(
        self,
        issue_id: str,
        new_status: IssueStatus,
        old_status: IssueStatus,
        issue_store: "IssueStore",
        project_manager: "ProjectManager | None" = None,
    ) -> None:
        self._issue_id = issue_id
        self._new_status = new_status
        self._old_status = old_status
        self._issue_store = issue_store
        self._project = project_manager

    def execute(self) -> None:
        self._issue_store.set_status(self._issue_id, self._new_status)

    def undo(self) -> None:
        self._issue_store.set_status(self._issue_id, self._old_status)

    @property
    def description(self) -> str:
        return f"Set issue {self._issue_id} → {self._new_status.value}"
