"""Core data model dataclasses.

All other modules import from here. Keep this module free of side-effects and
Qt imports so it can be used in tests and CLI contexts without a display.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    SUSPICION = "SUSPICION"

    def __lt__(self, other: "Severity") -> bool:
        order = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.SUSPICION: 2}
        return order[self] < order[other]

    def __le__(self, other: "Severity") -> bool:
        return self == other or self < other


class IssueStatus(str, Enum):
    OPEN = "OPEN"
    FIXED = "FIXED"
    IGNORED = "IGNORED"
    EXCEPTED = "EXCEPTED"


class ColumnKind(str, Enum):
    FREE_TEXT_SHORT = "free_text_short"
    FREE_TEXT_LONG = "free_text_long"
    CONTROLLED = "controlled"
    STRUCTURED = "structured"
    LIST = "list"


# ---------------------------------------------------------------------------
# Dataset metadata
# ---------------------------------------------------------------------------


@dataclass
class DatasetMeta:
    file_path: str
    encoding: str
    delimiter: str | None  # None for XLSX
    sheet_name: str | None  # None for CSV
    header_row: int  # 0-based index of the row used as column headers
    skip_rows: int  # number of rows before header_row that were skipped
    original_shape: tuple[int, int]  # (data_rows, cols) after header applied
    column_order: list[str]
    fingerprint: str  # sha256 of raw file bytes[:65536]


# ---------------------------------------------------------------------------
# Column metadata
# ---------------------------------------------------------------------------


@dataclass
class ColumnMeta:
    name: str
    kind: ColumnKind = ColumnKind.FREE_TEXT_SHORT
    required: bool = False
    unique: bool = False
    multiline_ok: bool = False
    allowed_values: list[str] = field(default_factory=list)
    regex: str | None = None
    list_separator: str = "|"
    violation_severity: Severity = Severity.WARNING
    nakala_field: str | None = None  # e.g. "nakala:type"


# ---------------------------------------------------------------------------
# Issue
# ---------------------------------------------------------------------------


@dataclass
class Issue:
    """A validation finding at a specific location in the dataset."""

    id: str  # deterministic sha256[:12] of (rule_id, col, row, original)
    rule_id: str  # e.g. "generic.hygiene.leading_space"
    severity: Severity
    status: IssueStatus
    row: int  # 0-based index into the data DataFrame
    col: str  # column name (display name = header value)
    original: Any  # cell value at discovery time (may be None)
    message: str
    suggestion: Any = None  # proposed fix value; None if no auto-fix
    extra: dict = field(default_factory=dict)  # rule-specific details

    @staticmethod
    def make_id(rule_id: str, col: str, row: int, original: Any) -> str:
        payload = json.dumps([rule_id, col, row, str(original)], ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:12]

    @classmethod
    def create(
        cls,
        rule_id: str,
        severity: Severity,
        row: int,
        col: str,
        original: Any,
        message: str,
        suggestion: Any = None,
        extra: dict | None = None,
    ) -> "Issue":
        return cls(
            id=cls.make_id(rule_id, col, row, original),
            rule_id=rule_id,
            severity=severity,
            status=IssueStatus.OPEN,
            row=row,
            col=col,
            original=original,
            message=message,
            suggestion=suggestion,
            extra=extra or {},
        )


# ---------------------------------------------------------------------------
# Patch (atomic single-cell change)
# ---------------------------------------------------------------------------


@dataclass
class Patch:
    """Represents one applied fix. Persisted as work/patches/<patch_id>.json."""

    patch_id: str
    action_id: str  # groups patches belonging to one user action
    row: int  # 0-based row in the data DataFrame
    col: str
    old_value: Any
    new_value: Any
    issue_id: str | None  # issue resolved by this patch (if any)
    timestamp: str  # ISO-8601 UTC

    def to_dict(self) -> dict:
        return {
            "patch_id": self.patch_id,
            "action_id": self.action_id,
            "row": self.row,
            "col": self.col,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "issue_id": self.issue_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Patch":
        return cls(**d)


# ---------------------------------------------------------------------------
# Action log entry
# ---------------------------------------------------------------------------


@dataclass
class ActionLogEntry:
    """One line of work/actions_log.jsonl."""

    action_id: str
    timestamp: str
    action_type: str  # "fix", "bulk_fix", "ignore", "except", "undo", "redo"
    scope: str  # "cell", "column", "global"
    params: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)  # e.g. {"cells_changed": 3}
    patch_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "timestamp": self.timestamp,
            "action_type": self.action_type,
            "scope": self.scope,
            "params": self.params,
            "stats": self.stats,
            "patch_ids": self.patch_ids,
        }
