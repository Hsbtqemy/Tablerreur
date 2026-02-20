"""Exporters: XLSX, CSV (always ;), TXT report, issues.csv."""

from __future__ import annotations

import csv
import io
import textwrap
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from spreadsheet_qa.core.models import DatasetMeta, Issue, IssueStatus, Severity

# ---------------------------------------------------------------------------
# Lazy import of UI strings (core must remain Qt-free; t() is pure Python)
# ---------------------------------------------------------------------------


def _t(key: str, **kwargs: object) -> str:
    """Resolve a UI string key.  Falls back to key if i18n not available."""
    try:
        from spreadsheet_qa.ui.i18n import t
        return t(key, **kwargs)
    except Exception:
        return key


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M")


# ---------------------------------------------------------------------------
# XLSX export
# ---------------------------------------------------------------------------


class XLSXExporter:
    """Export cleaned DataFrame to XLSX."""

    def export(self, df: pd.DataFrame, path: Path) -> None:
        import openpyxl
        from openpyxl.styles import Font

        path.parent.mkdir(parents=True, exist_ok=True)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = _t("xlsx.sheet.data")

        # Header row
        header_font = Font(bold=True)
        for col_idx, col_name in enumerate(df.columns, start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = header_font

        # Data rows
        for row_idx, row in enumerate(df.itertuples(index=False), start=2):
            for col_idx, val in enumerate(row, start=1):
                cell_val = "" if pd.isna(val) else str(val)
                ws.cell(row=row_idx, column=col_idx, value=cell_val)

        wb.save(path)


# ---------------------------------------------------------------------------
# CSV export (ALWAYS ; delimiter)
# ---------------------------------------------------------------------------


class CSVExporter:
    """Export cleaned DataFrame to CSV.

    Rules (non-negotiable):
    - Delimiter: ;
    - Quote char: "
    - Quoting: QUOTE_MINIMAL (cells with ; or " or newline are quoted)
    - Encoding: UTF-8 or UTF-8-BOM
    """

    def export(self, df: pd.DataFrame, path: Path, bom: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        encoding = "utf-8-sig" if bom else "utf-8"

        with path.open("w", encoding=encoding, newline="") as f:
            writer = csv.writer(f, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(list(df.columns))
            for row in df.itertuples(index=False, name=None):
                writer.writerow(["" if pd.isna(v) else str(v) for v in row])


# ---------------------------------------------------------------------------
# Issues CSV export (ALWAYS ; delimiter)
# ---------------------------------------------------------------------------


class IssuesCSVExporter:
    """Export issues list to CSV with ; delimiter — French column headers."""

    @property
    def _columns(self) -> list[str]:
        return [
            _t("csv.issue_id"),
            _t("csv.severity"),
            _t("csv.status"),
            _t("csv.rule_id"),
            _t("csv.row"),
            _t("csv.column"),
            _t("csv.message"),
            _t("csv.original_value"),
            _t("csv.suggestion"),
            _t("csv.detected_at"),
        ]

    def export(self, issues: list[Issue], path: Path, meta: DatasetMeta | None = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        ts = _now_stamp()

        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(self._columns)
            for issue in issues:
                writer.writerow([
                    issue.id,
                    issue.severity.value,
                    issue.status.value,
                    issue.rule_id,
                    issue.row + 1,  # 1-based for humans
                    issue.col,
                    issue.message,
                    str(issue.original) if issue.original is not None else "",
                    str(issue.suggestion) if issue.suggestion is not None else "",
                    ts,
                ])


# ---------------------------------------------------------------------------
# TXT report — French headings
# ---------------------------------------------------------------------------


class TXTReporter:
    """Generate a human-readable text report in French."""

    def export(
        self,
        issues: list[Issue],
        path: Path,
        meta: DatasetMeta | None = None,
        open_only: bool = True,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Header
        lines.append("=" * 72)
        lines.append(_t("report.header"))
        lines.append(f"{_t('report.generated')} {ts}")
        if meta:
            lines.append(f"{_t('report.source')} {meta.file_path}")
            lines.append(
                f"{_t('report.shape')} "
                f"{meta.original_shape[0]} lignes × {meta.original_shape[1]} colonnes"
            )
            lines.append(f"{_t('report.encoding')} {meta.encoding}")
        lines.append("=" * 72)
        lines.append("")

        filtered = [i for i in issues if i.status == IssueStatus.OPEN] if open_only else issues

        # Summary counts
        counts = Counter(i.severity for i in filtered)
        lines.append(_t("report.summary"))
        lines.append("-" * 40)
        severity_names = {
            Severity.ERROR: _t("severity.ERROR"),
            Severity.WARNING: _t("severity.WARNING"),
            Severity.SUSPICION: _t("severity.SUSPICION"),
        }
        for sev in [Severity.ERROR, Severity.WARNING, Severity.SUSPICION]:
            lines.append(f"  {severity_names[sev]:<16} {counts.get(sev, 0):>5}")
        lines.append(f"  {'TOTAL':<16} {len(filtered):>5}")
        lines.append("")

        # Top columns
        col_counts = Counter(i.col for i in filtered)
        if col_counts:
            lines.append(_t("report.top_cols"))
            lines.append("-" * 40)
            for col, cnt in col_counts.most_common(10):
                lines.append(f"  {col:<35} {cnt:>5} {_t('report.issue_count')}")
            lines.append("")

        # Top issue types
        type_counts = Counter(i.rule_id for i in filtered)
        if type_counts:
            lines.append(_t("report.top_types"))
            lines.append("-" * 40)
            for rule_id, cnt in type_counts.most_common(10):
                lines.append(f"  {rule_id:<45} {cnt:>5}")
            lines.append("")

        # Details (grouped by severity)
        lines.append(_t("report.details"))
        lines.append("=" * 72)
        for sev in [Severity.ERROR, Severity.WARNING, Severity.SUSPICION]:
            sev_issues = [i for i in filtered if i.severity == sev]
            if not sev_issues:
                continue
            sev_name = severity_names[sev]
            lines.append(f"\n[{sev_name}] — {len(sev_issues)} {_t('report.issue_count')}")
            lines.append("-" * 40)
            for issue in sev_issues[:200]:  # cap per severity
                loc = f"{_t('report.row')} {issue.row + 1}, «{issue.col}»"
                lines.append(f"  {loc}")
                lines.append(f"    {issue.message}")
                if issue.suggestion is not None:
                    lines.append(f"    {_t('report.suggestion')} {issue.suggestion!r}")
                lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")
