"""ProjectManager: project folder creation, persistence, and action log."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

from spreadsheet_qa.core.models import ActionLogEntry, DatasetMeta, IssueStatus

_log = logging.getLogger(__name__)


class ProjectManager:
    """Manages a Tablerreur project folder."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder
        self._ensure_structure()

    @property
    def folder(self) -> Path:
        return self._folder

    @property
    def patches_dir(self) -> Path:
        return self._folder / "work" / "patches"

    @property
    def reports_dir(self) -> Path:
        return self._folder / "reports"

    @property
    def exports_dir(self) -> Path:
        return self._folder / "exports"

    @property
    def input_dir(self) -> Path:
        return self._folder / "input"

    @property
    def templates_dir(self) -> Path:
        return self._folder / "templates"

    def _ensure_structure(self) -> None:
        for subdir in ["work/patches", "work/patches/undone", "reports", "exports", "input", "templates"]:
            (self._folder / subdir).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # project.yml
    # ------------------------------------------------------------------

    def save_project_yml(
        self,
        meta: DatasetMeta,
        template: str = "generic",
        overlay: str | None = None,
        active_generic_template: str = "generic_default",
        active_overlay_template: str | None = None,
    ) -> None:
        data = {
            "version": 1,
            "source_file": meta.file_path,
            "template": template,
            "overlay": overlay,
            "active_generic_template": active_generic_template,
            "active_overlay_template": active_overlay_template,
            "header_row": meta.header_row + 1,  # 1-based for humans
            "encoding": meta.encoding,
            "delimiter": meta.delimiter,
            "sheet_name": meta.sheet_name,
            "fingerprint": meta.fingerprint,
            "created_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        }
        path = self._folder / "project.yml"
        path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def load_project_yml(self) -> dict:
        path = self._folder / "project.yml"
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    # ------------------------------------------------------------------
    # actions_log.jsonl
    # ------------------------------------------------------------------

    def append_action_log(self, entry: ActionLogEntry) -> None:
        log_path = self._folder / "work" / "actions_log.jsonl"
        line = json.dumps(entry.to_dict(), ensure_ascii=False)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def read_action_log(self) -> list[dict]:
        log_path = self._folder / "work" / "actions_log.jsonl"
        if not log_path.exists():
            return []
        entries = []
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    _log.debug("Skipping invalid JSON line in action log: %s — %s", line[:80], exc)
        return entries

    # ------------------------------------------------------------------
    # exceptions.yml
    # ------------------------------------------------------------------

    def load_exceptions(self) -> dict:
        path = self._folder / "work" / "exceptions.yml"
        if not path.exists():
            return {
                "cell_exceptions": [],
                "value_exceptions": [],
                "column_ignores": [],
                "global_ignores": [],
                "ignored_issues": [],
            }
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def save_exceptions(self, data: dict) -> None:
        path = self._folder / "work" / "exceptions.yml"
        path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def add_exception(self, issue_id: str, reason: str = "") -> None:
        exc = self.load_exceptions()
        cell_exc = exc.setdefault("cell_exceptions", [])
        if issue_id not in [e.get("issue_id") for e in cell_exc]:
            cell_exc.append({"issue_id": issue_id, "reason": reason})
        self.save_exceptions(exc)

    def add_ignored(self, issue_id: str) -> None:
        exc = self.load_exceptions()
        ignored = exc.setdefault("ignored_issues", [])
        if issue_id not in ignored:
            ignored.append(issue_id)
        self.save_exceptions(exc)

    def apply_exceptions_to_store(self, issue_store) -> None:
        """Load exceptions.yml and apply persisted EXCEPTED/IGNORED statuses."""
        exc = self.load_exceptions()
        for entry in exc.get("cell_exceptions", []):
            issue_id = entry.get("issue_id")
            if issue_id:
                issue_store.set_status(issue_id, IssueStatus.EXCEPTED)
        for issue_id in exc.get("ignored_issues", []):
            if issue_id:
                issue_store.set_status(issue_id, IssueStatus.IGNORED)

    # ------------------------------------------------------------------
    # Input file management
    # ------------------------------------------------------------------

    def copy_input_file(self, source_path: Path) -> Path:
        """Copy source file to project input/ directory."""
        dest = self._folder / "input" / source_path.name
        if dest.resolve() != source_path.resolve():
            shutil.copy2(source_path, dest)
        return dest


class NullProjectManager:
    """No-op project manager for when no project folder is open."""

    @property
    def patches_dir(self) -> Path:
        return Path("/tmp/spreadsheet_qa_patches")

    def append_action_log(self, entry: ActionLogEntry) -> None:
        pass

    def add_exception(self, issue_id: str, reason: str = "") -> None:
        pass

    def add_ignored(self, issue_id: str) -> None:
        pass

    def apply_exceptions_to_store(self, issue_store) -> None:
        pass

    def load_exceptions(self) -> dict:
        return {}
