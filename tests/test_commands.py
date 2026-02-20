"""Tests for the Command/History system (undo/redo)."""

from __future__ import annotations

import pandas as pd
import pytest

from spreadsheet_qa.core.commands import ApplyCellFixCommand, BulkCellFixCommand
from spreadsheet_qa.core.history import CommandHistory
from spreadsheet_qa.core.issue_store import IssueStore
from spreadsheet_qa.core.patch import NullPatchWriter


def _make_fix_command(df, row, col, old_val, new_val):
    return ApplyCellFixCommand(
        df=df,
        row=row,
        col=col,
        old_value=old_val,
        new_value=new_val,
        issue_store=IssueStore(),
        patch_writer=NullPatchWriter(),
    )


class TestApplyCellFixCommand:
    def test_execute_changes_df(self):
        df = pd.DataFrame({"A": ["old"]})
        cmd = _make_fix_command(df, 0, "A", "old", "new")
        cmd.execute()
        assert df.at[0, "A"] == "new"

    def test_undo_restores_df(self):
        df = pd.DataFrame({"A": ["original"]})
        cmd = _make_fix_command(df, 0, "A", "original", "changed")
        cmd.execute()
        assert df.at[0, "A"] == "changed"
        cmd.undo()
        assert df.at[0, "A"] == "original"

    def test_description_is_informative(self):
        df = pd.DataFrame({"Col": ["a"]})
        cmd = _make_fix_command(df, 0, "Col", "a", "b")
        assert "Col" in cmd.description
        assert "a" in cmd.description
        assert "b" in cmd.description


class TestCommandHistory:
    def test_push_executes_command(self):
        df = pd.DataFrame({"A": ["old"]})
        history = CommandHistory()
        cmd = _make_fix_command(df, 0, "A", "old", "new")
        history.push(cmd)
        assert df.at[0, "A"] == "new"
        assert history.can_undo
        assert not history.can_redo

    def test_undo(self):
        df = pd.DataFrame({"A": ["original"]})
        history = CommandHistory()
        cmd = _make_fix_command(df, 0, "A", "original", "modified")
        history.push(cmd)
        history.undo()
        assert df.at[0, "A"] == "original"
        assert not history.can_undo
        assert history.can_redo

    def test_redo(self):
        df = pd.DataFrame({"A": ["start"]})
        history = CommandHistory()
        cmd = _make_fix_command(df, 0, "A", "start", "end")
        history.push(cmd)
        history.undo()
        history.redo()
        assert df.at[0, "A"] == "end"

    def test_new_push_clears_redo_stack(self):
        df = pd.DataFrame({"A": ["a", "b"]})
        history = CommandHistory()
        cmd1 = _make_fix_command(df, 0, "A", "a", "x")
        cmd2 = _make_fix_command(df, 1, "A", "b", "y")
        history.push(cmd1)
        history.undo()
        assert history.can_redo
        history.push(cmd2)
        assert not history.can_redo

    def test_undo_on_empty_history_returns_none(self):
        history = CommandHistory()
        result = history.undo()
        assert result is None

    def test_max_depth_respected(self):
        df = pd.DataFrame({"A": [str(i) for i in range(200)]})
        history = CommandHistory(max_depth=10)
        for i in range(15):
            cmd = _make_fix_command(df, i % 5, "A", df.at[i % 5, "A"], f"v{i}")
            history.push(cmd)
        # Stack should cap at 10, not exceed
        assert history.undo_count <= 10

    def test_df_identity_preserved(self):
        """The command must hold a reference to the original df, not a copy."""
        df = pd.DataFrame({"A": ["a"]})
        cmd = _make_fix_command(df, 0, "A", "a", "b")
        assert cmd._df is df
