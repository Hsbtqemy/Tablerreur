"""Tests for patch file write/read/delete cycle."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from spreadsheet_qa.core.models import Patch
from spreadsheet_qa.core.patch import NullPatchWriter, PatchWriter


def _make_patch(patch_id="abc123", row=5, col="Titre", old_val="old", new_val="new"):
    return Patch(
        patch_id=patch_id,
        action_id="action01",
        row=row,
        col=col,
        old_value=old_val,
        new_value=new_val,
        issue_id="issue01",
        timestamp=datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
    )


class TestPatchWriter:
    def test_write_creates_json_file(self, tmp_path):
        pw = PatchWriter(tmp_path / "patches")
        patch = _make_patch()
        path = pw.write(patch)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["patch_id"] == "abc123"

    def test_read_returns_patch(self, tmp_path):
        pw = PatchWriter(tmp_path / "patches")
        patch = _make_patch("xyz789")
        pw.write(patch)
        restored = pw.read("xyz789")
        assert restored is not None
        assert restored.patch_id == "xyz789"
        assert restored.col == "Titre"

    def test_delete_moves_to_undone(self, tmp_path):
        patches_dir = tmp_path / "patches"
        pw = PatchWriter(patches_dir)
        patch = _make_patch("to_delete")
        pw.write(patch)
        pw.delete("to_delete")
        # Original file should be gone
        assert not (patches_dir / "to_delete.json").exists()
        # File should be in undone/
        assert (patches_dir / "undone" / "to_delete.json").exists()

    def test_all_patches(self, tmp_path):
        pw = PatchWriter(tmp_path / "patches")
        for i in range(3):
            pw.write(_make_patch(patch_id=f"p{i}"))
        patches = pw.all_patches()
        assert len(patches) == 3

    def test_patch_roundtrip_preserves_data(self, tmp_path):
        pw = PatchWriter(tmp_path / "patches")
        original = _make_patch(row=42, col="Description", old_val="original text", new_val="fixed")
        pw.write(original)
        restored = pw.read(original.patch_id)
        assert restored.row == 42
        assert restored.col == "Description"
        assert restored.old_value == "original text"
        assert restored.new_value == "fixed"


class TestNullPatchWriter:
    def test_write_returns_none(self):
        nw = NullPatchWriter()
        patch = _make_patch()
        result = nw.write(patch)
        assert result is None  # no-op: no project folder open

    def test_delete_does_not_raise(self):
        nw = NullPatchWriter()
        nw.delete("nonexistent")  # should not raise

    def test_all_patches_returns_empty(self):
        nw = NullPatchWriter()
        assert nw.all_patches() == []
