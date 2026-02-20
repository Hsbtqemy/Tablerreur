"""CommandHistory: undo/redo stack."""

from __future__ import annotations

from collections import deque

from spreadsheet_qa.core.commands import Command


class CommandHistory:
    """Manages a bounded undo/redo stack."""

    def __init__(self, max_depth: int = 500) -> None:
        self._undo_stack: deque[Command] = deque(maxlen=max_depth)
        self._redo_stack: deque[Command] = deque(maxlen=max_depth)

    def push(self, cmd: Command) -> None:
        """Execute command and push to undo stack. Clears redo stack."""
        cmd.execute()
        self._undo_stack.append(cmd)
        self._redo_stack.clear()

    def undo(self) -> Command | None:
        """Undo the most recent command."""
        if not self._undo_stack:
            return None
        cmd = self._undo_stack.pop()
        cmd.undo()
        self._redo_stack.append(cmd)
        return cmd

    def redo(self) -> Command | None:
        """Re-execute the most recently undone command."""
        if not self._redo_stack:
            return None
        cmd = self._redo_stack.pop()
        cmd.execute()
        self._undo_stack.append(cmd)
        return cmd

    @property
    def undo_count(self) -> int:
        """Number of commands currently on the undo stack."""
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        """Number of commands currently on the redo stack."""
        return len(self._redo_stack)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def undo_description(self) -> str | None:
        return self._undo_stack[-1].description if self._undo_stack else None

    @property
    def redo_description(self) -> str | None:
        return self._redo_stack[-1].description if self._redo_stack else None

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
