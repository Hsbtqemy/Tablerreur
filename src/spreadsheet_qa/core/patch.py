"""Patch file management: write/read/delete JSON patch files in work/patches/."""

from __future__ import annotations

import json
import logging
from pathlib import Path

_log = logging.getLogger(__name__)

from spreadsheet_qa.core.models import Patch


class PatchWriter:
    """Write and delete patch files in a project's work/patches/ directory."""

    def __init__(self, patches_dir: Path) -> None:
        self._dir = patches_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def write(self, patch: Patch) -> Path | None:
        path = self._dir / f"{patch.patch_id}.json"
        path.write_text(json.dumps(patch.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def delete(self, patch_id: str) -> None:
        path = self._dir / f"{patch_id}.json"
        if path.exists():
            # Move to undone/ subfolder rather than hard-delete
            undone_dir = self._dir / "undone"
            undone_dir.mkdir(exist_ok=True)
            path.rename(undone_dir / path.name)

    def read(self, patch_id: str) -> Patch | None:
        path = self._dir / f"{patch_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Patch.from_dict(data)

    def all_patches(self) -> list[Patch]:
        patches = []
        for p in sorted(self._dir.glob("*.json")):
            try:
                patches.append(Patch.from_dict(json.loads(p.read_text(encoding="utf-8"))))
            except Exception as exc:
                _log.warning("Could not load patch file %s: %s", p, exc)
        return patches


class NullPatchWriter(PatchWriter):
    """No-op patch writer for use when no project folder is open."""

    def __init__(self) -> None:
        # Do not call super().__init__() — no directory needed
        pass

    def write(self, patch: Patch) -> None:  # type: ignore[override]
        """No-op: patch is not persisted when no project folder is open."""
        return None

    def delete(self, patch_id: str) -> None:
        pass

    def read(self, patch_id: str) -> Patch | None:
        return None

    def all_patches(self) -> list[Patch]:
        return []
