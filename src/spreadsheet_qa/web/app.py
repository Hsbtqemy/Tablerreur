"""Tablerreur Web App — FastAPI backend.

Workflow:
  POST /api/jobs            → upload file, create job → job_id
  PATCH /api/jobs/{id}/template → modèle builtin + overlay (après création)
  POST /api/jobs/{id}/fixes → apply hygiene fix pack
  POST /api/jobs/{id}/validate → run validation engine
  GET  /api/jobs/{id}       → job status / summary
  GET  /api/jobs/{id}/problems → paginated/filtered problem list
  GET  /api/jobs/{id}/download/{filename} → download outputs

Run with:
  uvicorn spreadsheet_qa.web.app:app --reload --port 8000
"""

from __future__ import annotations

import io
import logging
import os
import sys
import pickle
import re
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from spreadsheet_qa.core.commands import Command
from spreadsheet_qa.core.dataset import DatasetLoader, list_workbook_sheet_names_from_bytes
from spreadsheet_qa.core.engine import RuleFailure, ValidationEngine
from spreadsheet_qa.core.exporters import (
    AnnotatedXLSXExporter,
    CSVExporter,
    IssuesCSVExporter,
    TXTReporter,
    XLSXExporter,
    build_annotated_dataframe,
)
from spreadsheet_qa.core.format_detection import detect_column_format
from spreadsheet_qa.core.models import IssueStatus, Severity
from spreadsheet_qa.core.nakala_api import NakalaClient
from spreadsheet_qa.core.template_manager import TemplateManager
from spreadsheet_qa.core.text_utils import INVISIBLE_RE, UNICODE_SUSPECTS
from spreadsheet_qa.web.jobs import Job, JobState, ProblemRow, ValidationSummary, job_manager

# ---------------------------------------------------------------------------
# Configuration via variables d'environnement
# ---------------------------------------------------------------------------

_ENV = os.environ.get("TABLERREUR_ENV", "dev")

_MAX_UPLOAD_MB = int(os.environ.get("TABLERREUR_MAX_UPLOAD_MB", "50"))
_MAX_UPLOAD_BYTES = _MAX_UPLOAD_MB * 1024 * 1024

# Origines CORS : "*" = toutes, sinon liste séparée par virgules
_CORS_ORIGINS_RAW = os.environ.get("TABLERREUR_CORS_ORIGINS", "*")
_CORS_ORIGINS: list[str] = (
    ["*"]
    if _CORS_ORIGINS_RAW in ("*", "")
    else [o.strip() for o in _CORS_ORIGINS_RAW.split(",") if o.strip()]
)
# allow_credentials est incompatible avec allow_origins=["*"]
_CORS_ALLOW_CREDENTIALS = "*" not in _CORS_ORIGINS

# Extensions et types MIME acceptés pour l'upload
_ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".xlsm"}
# Classeurs pour lesquels une feuille peut être choisie à l'import
_WORKBOOK_EXTENSIONS = frozenset({".xlsx", ".xls", ".xlsm"})
# Les navigateurs et outils envoient parfois "application/octet-stream" pour
# les fichiers binaires — on accepte ce type générique et on se fie à l'extension.
_ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel.sheet.macroenabled.12",
    "application/vnd.ms-excel",
    "application/octet-stream",
    "binary/octet-stream",
}

_logger = logging.getLogger(__name__)


def _rule_failures_payload(rule_failures: list[RuleFailure]) -> list[dict[str, str | None]]:
    """Expose les règles en erreur à l'UI (sans détail technique)."""
    return [
        {
            "règle": rf.rule_id,
            "colonne": rf.column,
            "message": "Cette règle n'a pas pu s'exécuter (erreur interne).",
        }
        for rf in rule_failures
    ]


# ---------------------------------------------------------------------------
# WebBulkFixCommand — commande undo/redo pour les correctifs d'hygiène web
# ---------------------------------------------------------------------------

class WebBulkFixCommand(Command):
    """Wraps a batch of cell edits (hygiene fixes) as an undoable/redoable command.

    Rather than holding a live DataFrame reference, it stores the pickle path
    and applies / reverses each ``(row_idx, col, old_val, new_val)`` change by
    reloading and re-saving the pickle on every execute/undo call.
    This keeps the command serialisable-friendly and avoids stale df references.
    """

    def __init__(
        self,
        df_path: Path,
        changes: list[tuple],
        label: str = "Correctifs d'hygiène",
    ) -> None:
        self._df_path = df_path
        # list of (row_idx, col, old_val, new_val)
        self._changes = changes
        self._label = label

    def execute(self) -> None:
        df = pd.read_pickle(str(self._df_path))
        for row_idx, col, _, new_val in self._changes:
            df.at[row_idx, col] = new_val
        df.to_pickle(str(self._df_path))

    def undo(self) -> None:
        df = pd.read_pickle(str(self._df_path))
        for row_idx, col, old_val, _ in self._changes:
            df.at[row_idx, col] = old_val
        df.to_pickle(str(self._df_path))

    @property
    def description(self) -> str:
        return f"{self._label} ({len(self._changes)} cellule{'s' if len(self._changes) != 1 else ''})"

    @property
    def cells_count(self) -> int:
        return len(self._changes)

    @property
    def touched_rows(self) -> set[int]:
        return {int(row_idx) for row_idx, _, _, _ in self._changes}

    @property
    def touched_cells(self) -> set[tuple[int, str]]:
        return {(int(row_idx), str(col)) for row_idx, col, _, _ in self._changes}

# ---------------------------------------------------------------------------
# Client NAKALA — singleton avec cache disque
# ---------------------------------------------------------------------------

_nakala_cache_path = Path(
    os.environ.get(
        "TABLERREUR_NAKALA_CACHE",
        str(Path(tempfile.gettempdir()) / "tablerreur_nakala_cache.json"),
    )
)
_nakala_client = NakalaClient(cache_path=_nakala_cache_path)

# ---------------------------------------------------------------------------
# Application FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Tablerreur API",
    description="API de contrôle qualité pour tableurs CSV/XLSX",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=_CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the static frontend files.
# When run as a PyInstaller onedir sidecar, __file__ may not sit next to the
# bundled static files; the latter are at {exe_dir}/spreadsheet_qa/web/static.
if getattr(sys, "frozen", False):
    _base_dir = Path(sys.executable).parent
    _static_dir = _base_dir / "spreadsheet_qa" / "web" / "static"
else:
    _static_dir = Path(__file__).parent / "static"
if not _static_dir.is_dir():
    _logger.warning("Static directory not found: %s", _static_dir)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Mapala routes
from spreadsheet_qa.web.mapala_routes import router as mapala_router  # noqa: E402
app.include_router(mapala_router)


@app.on_event("startup")
async def _log_startup() -> None:
    _logger.info(
        "Tablerreur démarré — env=%s max_upload=%dMo cors=%s",
        _ENV,
        _MAX_UPLOAD_MB,
        _CORS_ORIGINS_RAW,
    )
    # Prefetch NAKALA vocabularies in background (cache on disk for subsequent requests)
    _nakala_client.fetch_all_async()


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def root():
    from fastapi.responses import HTMLResponse
    index = _static_dir / "index.html"
    return HTMLResponse(index.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    from spreadsheet_qa import __version__
    return {"status": "ok", "version": __version__}


# ---------------------------------------------------------------------------
# Dataset preview (used by the configure step)
# ---------------------------------------------------------------------------


@app.get("/api/jobs/{job_id}/preview")
async def preview_job(job_id: str, rows: int = 30):
    """Return the first *rows* rows of the DataFrame as a JSON-serialisable list."""
    job = _get_job(job_id)
    df = _load_df(job)
    n = min(max(1, rows), len(df))
    data_rows = [
        [("" if pd.isna(v) else str(v)) for v in df.iloc[i]]
        for i in range(n)
    ]
    return {
        "columns": list(df.columns),
        "rows": data_rows,
        "total_rows": len(df),
    }


# ---------------------------------------------------------------------------
# Column configuration (configure step)
# ---------------------------------------------------------------------------


_FORMAT_OVERRIDE_KEYS = (
    "content_type",
    "format_preset",
    "regex",
    "yes_no_true_values",
    "yes_no_false_values",
)


def _normalize_override_value(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, list) and not value:
        return None
    return value


def _canonicalize_format_config(config: dict[str, Any] | None) -> tuple[Any, Any, Any, Any, Any]:
    cfg = config or {}
    content_type = _normalize_override_value(cfg.get("content_type"))
    format_preset = _normalize_override_value(cfg.get("format_preset"))
    regex = _normalize_override_value(cfg.get("regex"))
    yes_no_true_values = _normalize_override_value(cfg.get("yes_no_true_values"))
    yes_no_false_values = _normalize_override_value(cfg.get("yes_no_false_values"))

    if content_type == "integer" and not format_preset:
        content_type = "number"
        format_preset = "integer"
    elif content_type == "decimal" and not format_preset:
        content_type = "number"
        format_preset = "decimal"
    elif content_type == "email" and not format_preset:
        content_type = "address"
        format_preset = "email_preset"
    elif content_type == "url" and not format_preset:
        content_type = "address"
        format_preset = "url"

    if format_preset and format_preset != "custom":
        regex = None
        if format_preset != "yes_no":
            yes_no_true_values = None
            yes_no_false_values = None
    else:
        yes_no_true_values = None
        yes_no_false_values = None

    return (
        content_type,
        format_preset,
        regex,
        yes_no_true_values,
        yes_no_false_values,
    )


def _has_manual_format_override(user_cfg: dict[str, Any], template_cfg: dict[str, Any]) -> bool:
    if not user_cfg:
        return False

    user_subset = {key: user_cfg.get(key) for key in _FORMAT_OVERRIDE_KEYS if key in user_cfg}
    if not user_subset:
        return False

    template_subset = {key: template_cfg.get(key) for key in _FORMAT_OVERRIDE_KEYS}
    return _canonicalize_format_config(user_subset) != _canonicalize_format_config(template_subset)


@app.get("/api/jobs/{job_id}/column-config")
async def get_column_config(job_id: str):
    """Return per-column config merging template defaults with user overrides."""
    job = _get_job(job_id)
    df = _load_df(job)

    # Get template-derived defaults
    try:
        mgr = TemplateManager()
        tpl_config = mgr.compile_config(
            generic_id=job.template_id,
            overlay_id=job.overlay_id,
            column_names=list(df.columns),
        )
        tpl_columns: dict = tpl_config.get("columns", {})
    except Exception:
        tpl_columns = {}

    result: dict = {}
    user_overrides: dict[str, bool] = {}
    user_format_overrides: dict[str, bool] = {}
    for col in job.columns:
        tpl = tpl_columns.get(col, {})
        user = job.column_config.get(col, {})
        user_overrides[col] = bool(user)
        user_format_overrides[col] = _has_manual_format_override(user, tpl)

        def _pick(key: str, default):
            # User override wins if set, else template, else default
            if key in user and user[key] is not None:
                return user[key]
            v = tpl.get(key)
            if v is not None and v != [] and v != "":
                return v
            return default

        result[col] = {
            "required": _pick("required", False),
            "content_type": _pick("content_type", None),
            "unique": _pick("unique", False),
            "multiline_ok": _pick("multiline_ok", False),
            "allowed_values": _pick("allowed_values", None),
            "allowed_values_locked": _pick("allowed_values_locked", False),
            "regex": _pick("regex", None),
            "format_preset": _pick("format_preset", None),
            "min_length": _pick("min_length", None),
            "max_length": _pick("max_length", None),
            "forbidden_chars": _pick("forbidden_chars", None),
            "expected_case": _pick("expected_case", None),
            "yes_no_true_values": _pick("yes_no_true_values", None),
            "yes_no_false_values": _pick("yes_no_false_values", None),
            "list_separator": _pick("list_separator", None),
            "list_unique": _pick("list_unique", False),
            "list_no_empty": _pick("list_no_empty", True),
            "list_min_items": _pick("list_min_items", None),
            "list_max_items": _pick("list_max_items", None),
            "nakala_vocabulary": _pick("nakala_vocabulary", None),
            "detect_rare_values": _pick("detect_rare_values", False),
            "rare_threshold": _pick("rare_threshold", 1),
            "rare_min_total": _pick("rare_min_total", 10),
            "detect_similar_values": _pick("detect_similar_values", False),
            "similar_threshold": _pick("similar_threshold", 85),
        }

    return {
        "columns": result,
        "user_overrides": user_overrides,
        "user_format_overrides": user_format_overrides,
    }


@app.put("/api/jobs/{job_id}/column-config")
async def update_column_config(job_id: str, request: Request):
    """Merge partial per-column config into the job's column_config store."""
    job = _get_job(job_id)
    body = await request.json()
    columns_updates: dict = body.get("columns", {})

    for col, cfg in columns_updates.items():
        if col not in job.column_config:
            job.column_config[col] = {}
        for key, val in cfg.items():
            job.column_config[col][key] = val

    job_manager.update(job)
    return {"ok": True}


class JobTemplateUpdate(BaseModel):
    """Mise à jour du modèle de validation (étape Configurer — FLUX backlog §12)."""

    template_id: str = "generic_default"
    overlay_id: str | None = None


class AnnotatedExportRequest(BaseModel):
    scope: str = "all"
    include_visual_marks: bool = True
    include_status_column: bool = True
    only_open: bool = True
    format: str = "xlsx"


class IssuesReportExportRequest(BaseModel):
    scope: str = "all"
    only_open: bool = True
    format: str = "csv"


@app.patch("/api/jobs/{job_id}/template")
async def update_job_template(job_id: str, body: JobTemplateUpdate):
    """Définit le modèle builtin et l’overlay NAKALA optionnel après création du job."""
    job = _get_job(job_id)
    job.template_id = body.template_id
    oid = (body.overlay_id or "").strip()
    job.overlay_id = oid or None
    job_manager.update(job)
    return {"ok": True, "template_id": job.template_id, "overlay_id": job.overlay_id}


# ---------------------------------------------------------------------------
# Preview rule impact on a single column
# ---------------------------------------------------------------------------


@app.post("/api/jobs/{job_id}/preview-rule")
async def preview_rule(job_id: str, request: Request):
    """Preview the impact of a column config on actual column data.

    Returns 3 sample OK values and 3 sample failing values with their messages,
    plus total counts of passing / failing rows.
    """
    job = _get_job(job_id)
    df = _load_df(job)
    body = await request.json()
    column: str = body.get("column", "")
    config: dict = body.get("config", {})

    if not column or column not in df.columns:
        raise HTTPException(status_code=400, detail="Colonne introuvable")

    # Import individual rules (lazy, avoids circular imports at module level)
    from spreadsheet_qa.core.rules.content_type import ContentTypeRule
    from spreadsheet_qa.core.rules.duplicates import UniqueColumnRule
    from spreadsheet_qa.core.rules.required import RequiredRule
    from spreadsheet_qa.core.rules.soft_typing import SoftTypingRule
    from spreadsheet_qa.core.rules.regex_rule import RegexRule
    from spreadsheet_qa.core.rules.allowed_values import AllowedValuesRule
    from spreadsheet_qa.core.rules.length import LengthRule
    from spreadsheet_qa.core.rules.forbidden_chars import ForbiddenCharsRule
    from spreadsheet_qa.core.rules.case_rule import CaseRule
    from spreadsheet_qa.core.rules.list_items import ListItemsRule
    from spreadsheet_qa.core.rules.multiline import UnexpectedMultilineRule
    from spreadsheet_qa.core.rules.rare_values import RareValuesRule
    from spreadsheet_qa.core.rules.similar_values import SimilarValuesRule

    # For SoftTypingRule use a lower min_count so it fires on small datasets
    preview_config = {"min_count": 5, **config}

    rules = [
        RequiredRule(),
        UniqueColumnRule(),
        ContentTypeRule(),
        RegexRule(),
        AllowedValuesRule(),
        LengthRule(),
        ForbiddenCharsRule(),
        CaseRule(),
        UnexpectedMultilineRule(),
        ListItemsRule(),
        RareValuesRule(),
        SimilarValuesRule(),
        SoftTypingRule(),
    ]

    all_issues = []
    for rule in rules:
        try:
            col_arg = column if rule.per_column else None
            issues = rule.check(df, col_arg, preview_config)
            all_issues.extend(issues)
        except Exception:
            pass

    fail_rows: set[int] = {i.row for i in all_issues}

    # 3 distinct OK samples (non-empty, non-failing)
    sample_ok: list[str] = []
    seen_ok: set[str] = set()
    for row_idx in df.index:
        if row_idx not in fail_rows:
            val = df.at[row_idx, column]
            if not pd.isna(val) and str(val).strip():
                v = str(val).strip()
                if v not in seen_ok:
                    seen_ok.add(v)
                    sample_ok.append(v)
            if len(sample_ok) >= 3:
                break

    # 3 distinct fail samples (row → first issue)
    row_first_issue: dict[int, Any] = {}
    for issue in all_issues:
        if issue.row not in row_first_issue:
            row_first_issue[issue.row] = issue

    sample_fail: list[dict] = []
    seen_fail: set[tuple] = set()
    for row_idx in sorted(row_first_issue):
        issue = row_first_issue[row_idx]
        raw = df.at[row_idx, column]
        val = "" if pd.isna(raw) else str(raw)
        key = (val[:60], issue.message[:120])
        if key not in seen_fail:
            seen_fail.add(key)
            sample_fail.append({"value": val, "message": issue.message})
        if len(sample_fail) >= 3:
            break

    total_rows = len(df)
    total_fail = len(fail_rows)
    total_ok = total_rows - total_fail

    return {
        "sample_ok": sample_ok,
        "sample_fail": sample_fail,
        "total_ok": total_ok,
        "total_fail": total_fail,
    }


@app.post("/api/jobs/{job_id}/detect-format")
async def detect_format(job_id: str, request: Request):
    """Suggest a content type / format preset for one column."""
    job = _get_job(job_id)
    df = _load_df(job)
    body = await request.json()
    column: str = body.get("column", "")

    if not column or column not in df.columns:
        raise HTTPException(status_code=400, detail="Colonne introuvable")

    return detect_column_format(df[column], column_name=column)


# ---------------------------------------------------------------------------
# Job creation (upload)
# ---------------------------------------------------------------------------


@app.post("/api/inspect-workbook-sheets")
async def inspect_workbook_sheets(file: UploadFile = File(...)):
    """Liste les feuilles d'un classeur Excel (sélection avant téléversement du job)."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _WORKBOOK_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Ce service ne s'applique qu'aux classeurs Excel (XLSX, XLS, XLSM).",
        )
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct and ct not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Type de fichier non pris en charge. Formats acceptés : CSV, XLSX, XLS, XLSM.",
        )
    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Le fichier dépasse la taille maximale autorisée ({_MAX_UPLOAD_MB} Mo).",
        )
    sheets = list_workbook_sheet_names_from_bytes(content, file.filename or "")
    return {"sheets": sheets}


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    header_row: int = Form(1),
    delimiter: str = Form(""),
    encoding: str = Form(""),
    template_id: str = Form("generic_default"),
    overlay_id: str = Form(""),
    sheet_name: str = Form(""),
):
    """Upload a file and create a new validation job."""
    # --- Validation du type de fichier (avant création du job) ---
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Type de fichier non pris en charge. Formats acceptés : CSV, XLSX, XLS, XLSM.",
        )
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct and ct not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Type de fichier non pris en charge. Formats acceptés : CSV, XLSX, XLS, XLSM.",
        )

    # --- Lecture et vérification de la taille ---
    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Le fichier dépasse la taille maximale autorisée ({_MAX_UPLOAD_MB} Mo).",
        )

    job = job_manager.create()
    job.state = JobState.LOADING
    job.filename = file.filename or "fichier"
    job.template_id = template_id
    job.overlay_id = overlay_id or None

    # Save upload
    upload_path = job.work_dir / f"input{suffix}"
    upload_path.write_bytes(content)
    job.upload_path = upload_path

    # Load with DatasetLoader
    try:
        loader = DatasetLoader()
        load_kw: dict[str, Any] = {
            "path": upload_path,
            "header_row": max(0, header_row - 1),
            "encoding_hint": encoding or None,
            "delimiter_hint": delimiter or None,
        }
        if suffix in _WORKBOOK_EXTENSIONS:
            sn = (sheet_name or "").strip()
            load_kw["sheet_name"] = sn if sn else 0
        df, meta = loader.load(**load_kw)
    except Exception as exc:
        job.state = JobState.ERROR
        job.error_msg = str(exc)
        job_manager.update(job)
        raise HTTPException(status_code=422, detail=str(exc))

    job.rows = meta.original_shape[0]
    job.cols = meta.original_shape[1]
    job.columns = list(df.columns)
    job.state = JobState.PENDING

    # Pickle the DataFrame for downstream steps
    df_path = job.work_dir / "df.pkl"
    df.to_pickle(str(df_path))
    job._df_path = df_path

    job_manager.update(job)
    return {
        "job_id": job.id,
        "filename": job.filename,
        "rows": job.rows,
        "cols": job.cols,
        "columns": job.columns,
        "state": job.state.value,
    }


# ---------------------------------------------------------------------------
# Apply fix pack
# ---------------------------------------------------------------------------


@app.post("/api/jobs/{job_id}/fixes")
async def apply_fixes(
    job_id: str,
    trim: bool = Form(False),
    collapse_spaces: bool = Form(False),
    replace_nbsp: bool = Form(False),
    strip_invisible: bool = Form(False),
    normalize_unicode: bool = Form(False),
    normalize_newlines: bool = Form(False),
    columns: str = Form(""),  # comma-separated column names, empty = all
):
    """Apply selected hygiene fixes to the dataset."""
    job = _get_job(job_id)
    df = _load_df(job)
    job.state = JobState.FIXING

    target_cols = [c.strip() for c in columns.split(",") if c.strip()] if columns else list(df.columns)

    fixes_applied = {
        "trim": trim,
        "collapse_spaces": collapse_spaces,
        "replace_nbsp": replace_nbsp,
        "strip_invisible": strip_invisible,
        "normalize_unicode": normalize_unicode,
        "normalize_newlines": normalize_newlines,
    }
    job.fixes_applied = fixes_applied

    # Compute changes (before/after) without modifying df in-place
    changes: list[tuple] = []
    for col in target_cols:
        if col not in df.columns:
            continue
        for row_idx in df.index:
            val = df.at[row_idx, col]
            if pd.isna(val):
                continue
            orig = str(val)
            fixed = _apply_fixes(orig, fixes_applied)
            if fixed != orig:
                changes.append((row_idx, col, orig, fixed))

    if changes:
        # CommandHistory.push() calls execute() → applies changes + saves pickle
        cmd = WebBulkFixCommand(job._df_path, changes)
        job.command_history.push(cmd)

    job.cells_fixed = len(changes)
    job.state = JobState.PENDING
    job_manager.update(job)

    return {"cells_fixed": len(changes), "state": job.state.value}


def _apply_fixes(value: str, opts: dict[str, bool]) -> str:
    if opts.get("trim"):
        value = value.strip()
    if opts.get("collapse_spaces"):
        value = re.sub(r"  +", " ", value).strip()
    if opts.get("replace_nbsp"):
        value = value.replace("\u00a0", " ")
    if opts.get("strip_invisible"):
        value = INVISIBLE_RE.sub("", value)
    if opts.get("normalize_unicode"):
        for ch, rep in UNICODE_SUSPECTS.items():
            value = value.replace(ch, rep)
        value = unicodedata.normalize("NFC", value)
    if opts.get("normalize_newlines"):
        value = value.replace("\r\n", "\n").replace("\r", "\n")
    return value


@app.get("/api/jobs/{job_id}/history")
async def get_fix_history(job_id: str):
    """Return the current undo/redo state for a job's fix history."""
    job = _get_job(job_id)
    h = job.command_history
    return {
        "can_undo": h.can_undo,
        "can_redo": h.can_redo,
        "undo_count": h.undo_count,
        "redo_count": h.redo_count,
    }


@app.post("/api/jobs/{job_id}/undo")
async def undo_fix(job_id: str):
    """Undo the last applied fix batch."""
    job = _get_job(job_id)
    h = job.command_history
    if not h.can_undo:
        return {
            "success": False,
            "message": "Rien à annuler.",
            "can_undo": False,
            "can_redo": h.can_redo,
        }
    h.undo()
    job_manager.update(job)
    return {
        "success": True,
        "action": "undo",
        "message": "Correctif annulé.",
        "can_undo": h.can_undo,
        "can_redo": h.can_redo,
    }


@app.post("/api/jobs/{job_id}/redo")
async def redo_fix(job_id: str):
    """Re-apply the last undone fix batch."""
    job = _get_job(job_id)
    h = job.command_history
    if not h.can_redo:
        return {
            "success": False,
            "message": "Rien à rétablir.",
            "can_undo": h.can_undo,
            "can_redo": False,
        }
    h.redo()
    job_manager.update(job)
    return {
        "success": True,
        "action": "redo",
        "message": "Correctif rétabli.",
        "can_undo": h.can_undo,
        "can_redo": h.can_redo,
    }


# ---------------------------------------------------------------------------
# Édition manuelle de cellules
# ---------------------------------------------------------------------------


@app.post("/api/jobs/{job_id}/edit-cell")
async def edit_cell(job_id: str, request: Request):
    """Modify a single cell and push the change to the undo/redo history."""
    job = _get_job(job_id)
    body = await request.json()
    row = body.get("row")
    column = body.get("column")
    value = body.get("value")

    if row is None or column is None or value is None:
        raise HTTPException(status_code=422, detail="Paramètres manquants : row, column, value")

    df = _load_df(job)
    if column not in df.columns:
        raise HTTPException(status_code=422, detail=f"Colonne inconnue : {column!r}")
    if not (isinstance(row, int) and 0 <= row < len(df)):
        raise HTTPException(status_code=422, detail=f"Ligne hors limites : {row}")

    cell_val = df.at[row, column]
    old_value = "" if pd.isna(cell_val) else str(cell_val)
    new_value = str(value)

    cmd = WebBulkFixCommand(
        job._df_path,
        [(row, column, old_value, new_value)],
        label=f"Édition manuelle — {column}[{row + 1}]",
    )
    job.command_history.push(cmd)
    job.exports_dirty = True
    job_manager.update(job)

    return {
        "success": True,
        "row": row,
        "column": column,
        "old_value": old_value,
        "new_value": new_value,
    }


@app.post("/api/jobs/{job_id}/edit-cells")
async def edit_cells(job_id: str, request: Request):
    """Modify multiple cells in a single undoable command."""
    job = _get_job(job_id)
    body = await request.json()
    edits: list[dict] = body.get("edits", [])

    if not edits:
        raise HTTPException(status_code=422, detail="La liste d'éditions est vide")

    df = _load_df(job)
    changes: list[tuple] = []
    results: list[dict] = []

    for edit in edits:
        row = edit.get("row")
        column = edit.get("column")
        value = edit.get("value")

        if row is None or column is None or value is None:
            raise HTTPException(status_code=422, detail="Paramètres manquants dans une édition")
        if column not in df.columns:
            raise HTTPException(status_code=422, detail=f"Colonne inconnue : {column!r}")
        if not (isinstance(row, int) and 0 <= row < len(df)):
            raise HTTPException(status_code=422, detail=f"Ligne hors limites : {row}")

        cell_val = df.at[row, column]
        old_value = "" if pd.isna(cell_val) else str(cell_val)
        new_value = str(value)
        changes.append((row, column, old_value, new_value))
        results.append({"row": row, "column": column, "old_value": old_value, "new_value": new_value})

    n = len(changes)
    cmd = WebBulkFixCommand(
        job._df_path,
        changes,
        label=f"Éditions manuelles en masse ({n} cellule{'s' if n != 1 else ''})",
    )
    job.command_history.push(cmd)
    job.exports_dirty = True
    job_manager.update(job)

    return {"success": True, "modifications": results}


@app.post("/api/jobs/{job_id}/fixes/preview")
async def preview_fixes(
    job_id: str,
    trim: bool = Form(False),
    collapse_spaces: bool = Form(False),
    replace_nbsp: bool = Form(False),
    strip_invisible: bool = Form(False),
    normalize_unicode: bool = Form(False),
    normalize_newlines: bool = Form(False),
    columns: str = Form(""),
    limit: int = Form(20),
):
    """Return a preview of which cells would be modified (without applying)."""
    job = _get_job(job_id)
    df = _load_df(job)

    opts = {
        "trim": trim,
        "collapse_spaces": collapse_spaces,
        "replace_nbsp": replace_nbsp,
        "strip_invisible": strip_invisible,
        "normalize_unicode": normalize_unicode,
        "normalize_newlines": normalize_newlines,
    }
    target_cols = [c.strip() for c in columns.split(",") if c.strip()] if columns else list(df.columns)

    preview: list[dict] = []
    for col in target_cols:
        if col not in df.columns:
            continue
        for row_idx in df.index:
            val = df.at[row_idx, col]
            if pd.isna(val):
                continue
            orig = str(val)
            fixed = _apply_fixes(orig, opts)
            if fixed != orig:
                preview.append({"colonne": col, "ligne": int(row_idx) + 1, "avant": orig, "après": fixed})
                if len(preview) >= limit:
                    break
        if len(preview) >= limit:
            break

    total = sum(
        1
        for col in target_cols
        if col in df.columns
        for row_idx in df.index
        if not pd.isna(df.at[row_idx, col]) and _apply_fixes(str(df.at[row_idx, col]), opts) != str(df.at[row_idx, col])
    )

    return {"total": total, "aperçu": preview}


_VALID_EXPORT_SCOPES = {"all", "issues", "blocking", "touched"}
_VALID_ANNOTATED_EXPORT_FORMATS = {"xlsx", "csv"}
_VALID_ISSUES_REPORT_FORMATS = {"csv", "txt"}


def _compile_validation_config(job: Job, df: pd.DataFrame) -> dict[str, Any]:
    mgr = TemplateManager()
    config = mgr.compile_config(
        generic_id=job.template_id,
        overlay_id=job.overlay_id,
        column_names=list(df.columns),
        nakala_client=_nakala_client,
    )
    if job.column_config:
        config_cols = config.setdefault("columns", {})
        for col, user_overrides in job.column_config.items():
            if col not in config_cols:
                config_cols[col] = {}
            for key, val in user_overrides.items():
                if val is not None:
                    config_cols[col][key] = val
    return config


def _run_validation_for_job(job: Job, df: pd.DataFrame) -> tuple[list, list[RuleFailure]]:
    engine = ValidationEngine()
    config = _compile_validation_config(job, df)
    result = engine.validate(df, config=config)
    return result.issues, result.rule_failures


def _build_summary_from_issues(issues: list) -> ValidationSummary:
    counts = {
        Severity.ERROR: 0,
        Severity.WARNING: 0,
        Severity.SUSPICION: 0,
    }
    for issue in issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1
    return ValidationSummary(
        errors=counts[Severity.ERROR],
        warnings=counts[Severity.WARNING],
        suspicions=counts[Severity.SUSPICION],
        total=len(issues),
    )


def _cell_str(df: pd.DataFrame, row_idx: int | None, col_name: str | None) -> str:
    if row_idx is None or not col_name:
        return ""
    try:
        if 0 <= row_idx < len(df) and col_name in df.columns:
            value = df.at[row_idx, col_name]
            if value is None:
                return ""
            rendered = str(value)
            return "" if rendered in ("<NA>", "nan") else rendered
    except Exception:
        pass
    return ""


def _build_problem_rows(df: pd.DataFrame, issues: list) -> list[ProblemRow]:
    return [
        ProblemRow(
            severity=issue.severity.value,
            status=issue.status.value,
            column=issue.col,
            row=issue.row + 1,
            message=issue.message,
            suggestion=str(issue.suggestion) if issue.suggestion is not None else "",
            issue_id=issue.id,
            valeur=_cell_str(df, issue.row, issue.col),
        )
        for issue in issues
    ]


def _save_issues_snapshot(job: Job, issues: list) -> None:
    issues_path = job.work_dir / "issues.pkl"
    with open(str(issues_path), "wb") as fh:
        pickle.dump(issues, fh)
    job._issues_path = issues_path


def _build_dataset_meta(job: Job):
    try:
        from spreadsheet_qa.core.models import DatasetMeta

        return DatasetMeta(
            file_path=str(job.upload_path),
            encoding="utf-8",
            delimiter=None,
            sheet_name=None,
            header_row=0,
            skip_rows=0,
            original_shape=(job.rows, job.cols),
            column_order=job.columns,
            fingerprint="",
        )
    except Exception as exc:
        _logger.warning("MÃ©tadonnÃ©es export : %s", exc)
        return None


def _apply_issue_status_overrides(issues: list, overrides: dict[str, str]) -> list:
    if not overrides:
        return list(issues)

    from dataclasses import replace as _dc_replace

    updated: list = []
    for issue in issues:
        status = overrides.get(issue.id)
        if not status:
            updated.append(issue)
            continue
        try:
            updated.append(_dc_replace(issue, status=IssueStatus(status)))
        except Exception:
            updated.append(issue)
    return updated


def _collect_touched_cells(job: Job) -> set[tuple[int, str]]:
    touched: set[tuple[int, str]] = set()
    history = getattr(job.command_history, "_undo_stack", [])
    for cmd in history:
        cells = getattr(cmd, "touched_cells", None)
        if cells:
            touched.update(cells)
            continue
        changes = getattr(cmd, "_changes", [])
        for row_idx, col, _, _ in changes:
            touched.add((int(row_idx), str(col)))
    return touched


def _normalize_export_scope(scope: str) -> str:
    normalized = (scope or "all").strip().lower()
    if normalized not in _VALID_EXPORT_SCOPES:
        raise HTTPException(
            status_code=422,
            detail="Scope invalide. Valeurs acceptÃ©es : all, issues, blocking, touched.",
        )
    return normalized


def _select_row_positions_for_export(
    df: pd.DataFrame,
    issues: list,
    scope: str,
    touched_rows: set[int],
) -> list[int]:
    if scope == "all":
        return list(range(len(df)))
    if scope == "touched":
        return sorted(row for row in touched_rows if 0 <= row < len(df))
    if scope == "blocking":
        return sorted({issue.row for issue in issues if issue.severity == Severity.ERROR})
    return sorted({issue.row for issue in issues})


def _filter_issues_for_export(issues: list, scope: str, touched_rows: set[int], only_open: bool) -> list:
    filtered = list(issues)
    if only_open:
        filtered = [issue for issue in filtered if issue.status == IssueStatus.OPEN]
    if scope == "blocking":
        filtered = [issue for issue in filtered if issue.severity == Severity.ERROR]
    elif scope == "touched":
        filtered = [issue for issue in filtered if issue.row in touched_rows]
    return filtered


def _safe_export_stem(filename: str | None) -> str:
    base = Path(filename or "tableur").stem.strip()
    cleaned = re.sub(r"[^\w.-]+", "_", base, flags=re.UNICODE).strip("._")
    return cleaned or "tableur"


def _work_export_path(job: Job, prefix: str, ext: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = job.work_dir / "exports_work"
    out_dir.mkdir(exist_ok=True)
    return out_dir / f"{prefix}_{_safe_export_stem(job.filename)}_{stamp}.{ext}"


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


@app.post("/api/jobs/{job_id}/validate")
async def validate_job(job_id: str):
    """Run the validation engine on the current DataFrame."""
    job = _get_job(job_id)
    df = _load_df(job)
    job.state = JobState.VALIDATING
    job_manager.update(job)

    try:
        issues, rule_failures = _run_validation_for_job(job, df)
    except Exception as exc:
        job.state = JobState.ERROR
        job.error_msg = str(exc)
        job_manager.update(job)
        raise HTTPException(status_code=500, detail=str(exc))

    job.summary = _build_summary_from_issues(issues)
    job.problems = _build_problem_rows(df, issues)
    _save_issues_snapshot(job, issues)
    job.issue_statuses = {}
    job.exports_dirty = False

    _generate_outputs(job, df, issues)

    job.error_msg = ""
    job.state = JobState.DONE
    job_manager.update(job)

    return {
        "state": job.state.value,
        "résumé": {
            "erreurs": job.summary.errors,
            "avertissements": job.summary.warnings,
            "suspicions": job.summary.suspicions,
            "total": job.summary.total,
        },
        "échecs_règles": _rule_failures_payload(rule_failures),
        "avertissements_export": job.export_errors,
    }


@app.post("/api/jobs/{job_id}/revalidate")
async def revalidate_job(job_id: str):
    """Re-run validation on the current DataFrame (after manual edits)."""
    job = _get_job(job_id)
    df = _load_df(job)

    try:
        issues, rule_failures = _run_validation_for_job(job, df)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    job.summary = _build_summary_from_issues(issues)
    job.problems = _build_problem_rows(df, issues)
    _save_issues_snapshot(job, issues)
    job.issue_statuses = {}
    job.exports_dirty = False

    _generate_outputs(job, df, issues)

    job.error_msg = ""
    job.state = JobState.DONE
    job_manager.update(job)

    return {
        "state": job.state.value,
        "résumé": {
            "erreurs": job.summary.errors,
            "avertissements": job.summary.warnings,
            "suspicions": job.summary.suspicions,
            "total": job.summary.total,
        },
        "échecs_règles": _rule_failures_payload(rule_failures),
        "avertissements_export": job.export_errors,
    }


def _generate_outputs(job: Job, df: pd.DataFrame, issues: list) -> None:
    """Pre-generate all downloadable files."""
    out = job.work_dir / "exports"
    out.mkdir(exist_ok=True)

    export_errors: list[str] = []

    meta = _build_dataset_meta(job)

    try:
        XLSXExporter().export(df, out / "nettoyé.xlsx")
    except Exception as exc:
        _logger.warning("Export XLSX : %s", exc)
        export_errors.append("Export Excel (nettoyé.xlsx) indisponible.")
    try:
        CSVExporter().export(df, out / "nettoyé.csv")
    except Exception as exc:
        _logger.warning("Export CSV : %s", exc)
        export_errors.append("Export CSV (nettoyé.csv) indisponible.")
    try:
        TXTReporter().export(issues, out / "rapport.txt", meta=meta)
    except Exception as exc:
        _logger.warning("Export rapport TXT : %s", exc)
        export_errors.append("Export du rapport texte indisponible.")
    try:
        IssuesCSVExporter().export(issues, out / "problèmes.csv", meta=meta)
    except Exception as exc:
        _logger.warning("Export problèmes CSV : %s", exc)
        export_errors.append("Export de la liste des problèmes (CSV) indisponible.")

    job.export_errors = export_errors


# ---------------------------------------------------------------------------
# Job status
# ---------------------------------------------------------------------------


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = _get_job(job_id)
    return {
        "job_id": job.id,
        "state": job.state.value,
        "filename": job.filename,
        "rows": job.rows,
        "cols": job.cols,
        "columns": job.columns,
        "template_id": job.template_id,
        "cells_fixed": job.cells_fixed,
        "résumé": {
            "erreurs": job.summary.errors,
            "avertissements": job.summary.warnings,
            "suspicions": job.summary.suspicions,
            "total": job.summary.total,
        } if job.state == JobState.DONE else None,
        "error": job.error_msg or None,
        "avertissements_export": job.export_errors if job.state == JobState.DONE else [],
    }


# ---------------------------------------------------------------------------
# Problems (paginated + filterable)
# ---------------------------------------------------------------------------


@app.get("/api/jobs/{job_id}/problems")
async def get_problems(
    job_id: str,
    page: int = 1,
    per_page: int = 50,
    severity: str = "",
    column: str = "",
    status: str = "",
):
    """Return a paginated, filtered list of problems for a job."""
    from collections import Counter

    job = _get_job(job_id)

    # Apply issue_statuses overrides to effective status
    overrides = job.issue_statuses
    effective: list[ProblemRow] = []
    for p in job.problems:
        eff_status = overrides.get(p.issue_id, p.status) if p.issue_id else p.status
        if eff_status != p.status:
            from dataclasses import replace as _dc_replace
            p = _dc_replace(p, status=eff_status)
        effective.append(p)

    # Status breakdown (before further filters)
    status_counts = Counter(p.status for p in effective)

    # Filters
    problems = effective
    if severity:
        problems = [p for p in problems if p.severity == severity]
    if column:
        problems = [p for p in problems if p.column == column]
    if status:
        problems = [p for p in problems if p.status == status]

    total = len(problems)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = problems[start:end]

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "statuts": {
            "OPEN": status_counts.get("OPEN", 0),
            "IGNORED": status_counts.get("IGNORED", 0),
            "EXCEPTED": status_counts.get("EXCEPTED", 0),
            "FIXED": status_counts.get("FIXED", 0),
        },
        "problèmes": [
            {
                "issue_id": p.issue_id,
                "sévérité": p.severity,
                "statut": p.status,
                "colonne": p.column,
                "ligne": p.row,
                "valeur": p.valeur,
                "message": p.message,
                "suggestion": p.suggestion,
            }
            for p in page_items
        ],
    }


# ---------------------------------------------------------------------------
# Issue status management
# ---------------------------------------------------------------------------

_VALID_USER_STATUSES = {"OPEN", "IGNORED", "EXCEPTED"}


@app.put("/api/jobs/{job_id}/issues/{issue_id}/status")
async def set_issue_status(job_id: str, issue_id: str, request: Request):
    """Set the status of a single issue (OPEN / IGNORED / EXCEPTED)."""
    job = _get_job(job_id)
    body = await request.json()
    new_status: str = body.get("status", "OPEN")

    if new_status not in _VALID_USER_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Statut invalide : {new_status!r}. Valeurs acceptées : OPEN, IGNORED, EXCEPTED.",
        )

    known_ids = {p.issue_id for p in job.problems if p.issue_id}
    if issue_id not in known_ids:
        raise HTTPException(status_code=404, detail="Problème introuvable")

    if new_status == "OPEN":
        job.issue_statuses.pop(issue_id, None)
    else:
        job.issue_statuses[issue_id] = new_status
    job.exports_dirty = True
    job_manager.update(job)
    return {"ok": True, "issue_id": issue_id, "status": new_status}


@app.put("/api/jobs/{job_id}/issues/bulk-status")
async def set_issues_bulk_status(job_id: str, request: Request):
    """Set the status of multiple issues at once."""
    job = _get_job(job_id)
    body = await request.json()
    issue_ids: list[str] = body.get("issue_ids", [])
    new_status: str = body.get("status", "IGNORED")

    if new_status not in _VALID_USER_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Statut invalide : {new_status!r}. Valeurs acceptées : OPEN, IGNORED, EXCEPTED.",
        )

    known_ids = {p.issue_id for p in job.problems if p.issue_id}
    changed = 0
    for iid in issue_ids:
        if iid in known_ids:
            if new_status == "OPEN":
                job.issue_statuses.pop(iid, None)
            else:
                job.issue_statuses[iid] = new_status
            changed += 1

    if changed:
        job.exports_dirty = True
        job_manager.update(job)

    return {"ok": True, "changed": changed, "status": new_status}


def _regenerate_status_exports(job: "Job") -> None:
    """Rebuild TXT report and issues CSV with updated issue statuses."""
    if not job._issues_path or not job._issues_path.exists():
        return
    try:
        with open(str(job._issues_path), "rb") as _fh:
            issues = pickle.load(_fh)
    except Exception as exc:
        _logger.warning("Régénération exports : lecture issues.pkl : %s", exc)
        return

    modified = _apply_issue_status_overrides(issues, job.issue_statuses)

    out = job.work_dir / "exports"
    meta = _build_dataset_meta(job)

    try:
        TXTReporter().export(modified, out / "rapport.txt", meta=meta)
    except Exception as exc:
        _logger.warning("Régénération rapport.txt : %s", exc)
    try:
        IssuesCSVExporter().export(modified, out / "problèmes.csv", meta=meta)
    except Exception as exc:
        _logger.warning("Régénération problèmes.csv : %s", exc)

    job.exports_dirty = False
    job_manager.update(job)


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------


@app.get("/api/jobs/{job_id}/download/{filename}")
async def download_file(job_id: str, filename: str):
    """Download a generated output file."""
    job = _get_job(job_id)
    exports_dir = job.work_dir / "exports"

    # Map allowed filenames
    allowed = {
        "rapport.txt": "rapport.txt",
        "problèmes.csv": "problèmes.csv",
        "nettoyé.xlsx": "nettoyé.xlsx",
        "nettoyé.csv": "nettoyé.csv",
        # URL-safe aliases
        "rapport": "rapport.txt",
        "problemes.csv": "problèmes.csv",
        "nettoye.xlsx": "nettoyé.xlsx",
        "nettoye.csv": "nettoyé.csv",
    }
    resolved = allowed.get(filename)
    if not resolved:
        raise HTTPException(status_code=404, detail="Fichier non trouvé")

    # Regenerate status-dependent exports when statuses have changed
    if job.exports_dirty and resolved in ("rapport.txt", "problèmes.csv"):
        _regenerate_status_exports(job)

    file_path = exports_dir / resolved
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier non encore généré")

    media_types = {
        ".txt": "text/plain; charset=utf-8",
        ".csv": "text/csv; charset=utf-8",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    media_type = media_types.get(file_path.suffix, "application/octet-stream")
    return FileResponse(str(file_path), media_type=media_type, filename=resolved)


@app.post("/api/jobs/{job_id}/exports/annotated")
async def export_annotated_workbook(job_id: str, body: AnnotatedExportRequest):
    """Generate an annotated work export from the current dataset state."""
    job = _get_job(job_id)
    df = _load_df(job)
    scope = _normalize_export_scope(body.scope)
    export_format = (body.format or "xlsx").strip().lower()
    if export_format not in _VALID_ANNOTATED_EXPORT_FORMATS:
        raise HTTPException(
            status_code=422,
            detail="Format invalide. Valeurs acceptées : xlsx, csv.",
        )

    try:
        issues, _ = _run_validation_for_job(job, df)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    effective_issues = _apply_issue_status_overrides(issues, job.issue_statuses)
    touched_cells = _collect_touched_cells(job)
    touched_rows = {row_idx for row_idx, _ in touched_cells}
    filtered_issues = _filter_issues_for_export(
        effective_issues,
        scope=scope,
        touched_rows=touched_rows,
        only_open=body.only_open,
    )
    row_positions = _select_row_positions_for_export(
        df,
        issues=filtered_issues,
        scope=scope,
        touched_rows=touched_rows,
    )

    if export_format == "xlsx":
        export_path = _work_export_path(job, f"tableur_annote_{scope}", "xlsx")
        AnnotatedXLSXExporter().export(
            df,
            export_path,
            filtered_issues,
            row_positions=row_positions,
            touched_cells=touched_cells,
            include_visual_marks=body.include_visual_marks,
            include_status_column=body.include_status_column,
        )
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        export_path = _work_export_path(job, f"tableur_annote_{scope}", "csv")
        annotated_df = build_annotated_dataframe(
            df,
            filtered_issues,
            row_positions=row_positions,
            include_status_column=body.include_status_column,
        )
        CSVExporter().export(annotated_df, export_path)
        media_type = "text/csv; charset=utf-8"

    return FileResponse(str(export_path), media_type=media_type, filename=export_path.name)


@app.post("/api/jobs/{job_id}/exports/issues-report")
async def export_issues_report(job_id: str, body: IssuesReportExportRequest):
    """Generate an issues report from the current dataset state."""
    job = _get_job(job_id)
    df = _load_df(job)
    scope = _normalize_export_scope(body.scope)
    export_format = (body.format or "csv").strip().lower()
    if export_format not in _VALID_ISSUES_REPORT_FORMATS:
        raise HTTPException(
            status_code=422,
            detail="Format invalide. Valeurs acceptées : csv, txt.",
        )

    try:
        issues, _ = _run_validation_for_job(job, df)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    effective_issues = _apply_issue_status_overrides(issues, job.issue_statuses)
    touched_cells = _collect_touched_cells(job)
    touched_rows = {row_idx for row_idx, _ in touched_cells}
    filtered_issues = _filter_issues_for_export(
        effective_issues,
        scope=scope,
        touched_rows=touched_rows,
        only_open=body.only_open,
    )
    meta = _build_dataset_meta(job)

    if export_format == "txt":
        export_path = _work_export_path(job, f"rapport_anomalies_{scope}", "txt")
        TXTReporter().export(filtered_issues, export_path, meta=meta, open_only=False)
        media_type = "text/plain; charset=utf-8"
    else:
        export_path = _work_export_path(job, f"rapport_anomalies_{scope}", "csv")
        IssuesCSVExporter().export(filtered_issues, export_path, meta=meta)
        media_type = "text/csv; charset=utf-8"

    return FileResponse(str(export_path), media_type=media_type, filename=export_path.name)


# ---------------------------------------------------------------------------
# Preview issues (cell-level highlights for the configure step)
# ---------------------------------------------------------------------------


@app.get("/api/jobs/{job_id}/preview-issues")
async def get_preview_issues(job_id: str, rows: int = 30):
    """Return cell-level issues for the first *rows* rows of the preview table.

    Only includes one issue per cell (the first one encountered).
    Results are sorted by row then column for determinism.
    """
    job = _get_job(job_id)
    if not job.problems:
        return {"cell_issues": []}

    cell_issues: list[dict] = []
    seen: set[tuple] = set()
    for p in job.problems:
        row_0based = p.row - 1  # ProblemRow.row is 1-based
        if row_0based < rows:
            key = (row_0based, p.column)
            if key not in seen:
                seen.add(key)
                cell_issues.append({
                    "row": row_0based,
                    "col": p.column,
                    "severity": p.severity.lower(),
                    "message": p.message,
                })

    cell_issues.sort(key=lambda x: (x["row"], x["col"]))
    return {"cell_issues": cell_issues}


# ---------------------------------------------------------------------------
# Vocabulaires NAKALA
# ---------------------------------------------------------------------------

_NAKALA_VOCAB_NAMES = {"datatypes", "licenses", "languages"}


@app.get("/api/nakala/vocabulary/{vocab_name}")
async def get_nakala_vocabulary(vocab_name: str):
    """Return the values of a NAKALA controlled vocabulary.

    vocab_name: "datatypes" | "licenses" | "languages"

    Returns {"values": [...], "count": N, "source": "NAKALA API"}.
    Returns 503 if the NAKALA API is unreachable and no cache is available.
    """
    if vocab_name not in _NAKALA_VOCAB_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"Vocabulaire inconnu : {vocab_name!r}. Valeurs acceptées : {sorted(_NAKALA_VOCAB_NAMES)}",
        )

    try:
        if vocab_name == "datatypes":
            values = _nakala_client.fetch_deposit_types()
        elif vocab_name == "licenses":
            values = _nakala_client.fetch_licenses()
        else:  # languages
            values = _nakala_client.fetch_languages()
    except Exception:
        values = []

    if not values:
        raise HTTPException(
            status_code=503,
            detail="Le vocabulaire NAKALA n'est pas disponible actuellement.",
        )

    result: dict[str, Any] = {"values": values, "count": len(values), "source": "NAKALA API"}

    # Pour les types de dépôt (datatypes), ajouter les libellés FR
    if vocab_name == "datatypes":
        from spreadsheet_qa.core.coar_mapping import COAR_URI_TO_LABEL_FR
        result["labels"] = {uri: COAR_URI_TO_LABEL_FR[uri] for uri in values if uri in COAR_URI_TO_LABEL_FR}

    return result


# ---------------------------------------------------------------------------
# Template export / import
# ---------------------------------------------------------------------------

# Default values for each column config key (used to strip noise from exports)
_COLUMN_DEFAULTS: dict[str, Any] = {
    "required": False,
    "unique": False,
    "multiline_ok": False,
    "content_type": None,
    "allowed_values": None,
    "allowed_values_locked": False,
    "regex": None,
    "format_preset": None,
    "yes_no_true_values": None,
    "yes_no_false_values": None,
    "min_length": None,
    "max_length": None,
    "forbidden_chars": None,
    "expected_case": None,
    "nakala_vocabulary": None,
    "list_separator": None,
    "list_unique": False,
    "list_no_empty": True,  # default True → excluded when True
    "list_min_items": None,
    "list_max_items": None,
    "detect_rare_values": False,
    "rare_threshold": 1,
    "rare_min_total": 10,
    "detect_similar_values": False,
    "similar_threshold": 85,
}

# Max size for imported template YAML files
_MAX_TEMPLATE_BYTES = 1 * 1024 * 1024  # 1 Mo


def _filter_column_defaults(cfg: dict) -> dict:
    """Return a copy of *cfg* with all default/empty values stripped out."""
    result: dict = {}
    for key, val in cfg.items():
        if val is None:
            continue
        if isinstance(val, list) and len(val) == 0:
            continue
        if isinstance(val, str) and val == "":
            continue
        default = _COLUMN_DEFAULTS.get(key)
        if val == default:
            continue
        result[key] = val
    return result


@app.get("/api/jobs/{job_id}/export-template")
async def export_template(job_id: str):
    """Export the current job column configuration as a reusable YAML template.

    Returns a YAML file as an attachment. Only non-default column config values
    are included, keeping the file human-readable and free of noise.
    """
    from fastapi.responses import Response

    job = _get_job(job_id)
    df = _load_df(job)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename_base = Path(job.filename).stem if job.filename else "tableur"

    # Compile active template rules for the rules section
    try:
        mgr = TemplateManager()
        tpl_config = mgr.compile_config(
            generic_id=job.template_id,
            overlay_id=job.overlay_id,
            column_names=list(df.columns),
        )
        template_rules: dict = tpl_config.get("rules", {})
    except Exception:
        template_rules = {}

    # Build per-column config (non-default values only)
    col_configs: dict = {}
    for col, cfg in job.column_config.items():
        if col not in df.columns:
            continue
        filtered = _filter_column_defaults(cfg)
        if filtered:
            col_configs[col] = filtered

    # Assemble template dict
    template: dict = {
        "name": "Mon modèle personnalisé",
        "description": f"Généré depuis Tablerreur le {date_str}",
        "type": "generic",
    }
    if template_rules:
        template["rules"] = template_rules
    if col_configs:
        template["columns"] = col_configs

    # Render YAML with a human-readable header comment
    header = (
        f"# Modèle Tablerreur\n"
        f"# Généré le : {date_str}\n"
        f"# Source : {job.filename or 'inconnu'}\n"
        f"# Pour réimporter : utilisez « Importer un modèle » à l'étape Configurer.\n\n"
    )
    yaml_content = header + yaml.dump(
        template,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    export_filename = f"template_{filename_base}_{date_str}.yml"
    return Response(
        content=yaml_content.encode("utf-8"),
        media_type="application/x-yaml",
        headers={"Content-Disposition": f'attachment; filename="{export_filename}"'},
    )


_MAX_VOCABULARY_BYTES = 5 * 1024 * 1024  # 5 Mo


@app.post("/api/jobs/{job_id}/import-vocabulary")
async def import_vocabulary(job_id: str, file: UploadFile = File(...)):
    """Import a vocabulary file (.yml/.yaml or .txt) and return the parsed list.

    Supported formats:
      - YAML dict: { name: str, values: [str, ...] }
      - YAML dict: { values: [str, ...] }
      - YAML bare list: [val1, val2, ...]
      - Plain text (.txt): one value per line

    Returns { name, values, count }.
    """
    _get_job(job_id)  # validate job exists

    content = await file.read()
    if len(content) > _MAX_VOCABULARY_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Le fichier dépasse la taille maximale autorisée (5 Mo).",
        )

    filename_lower = (file.filename or "").lower()
    text = content.decode("utf-8", errors="replace")

    # Plain text (.txt): one value per line, no YAML parsing
    if filename_lower.endswith(".txt"):
        values = [line.strip() for line in text.splitlines() if line.strip()]
        if not values:
            raise HTTPException(
                status_code=422,
                detail="Le fichier ne contient pas de liste de valeurs valide.",
            )
        name = Path(file.filename or "vocabulaire").stem
        return {"name": name, "values": values, "count": len(values)}

    # YAML
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        raise HTTPException(
            status_code=422,
            detail="Le fichier ne contient pas de liste de valeurs valide.",
        )

    values: list[str] | None = None
    name = "Vocabulaire importé"

    if isinstance(data, list):
        values = [str(v) for v in data if v is not None]
    elif isinstance(data, dict):
        if "name" in data and isinstance(data["name"], str):
            name = data["name"]
        raw = data.get("values")
        if isinstance(raw, list):
            values = [str(v) for v in raw if v is not None]

    if not values:
        raise HTTPException(
            status_code=422,
            detail="Le fichier ne contient pas de liste de valeurs valide.",
        )

    return {"name": name, "values": values, "count": len(values)}


@app.post("/api/jobs/{job_id}/import-template")
async def import_template(job_id: str, file: UploadFile = File(...)):
    """Import a YAML template and apply matching column configs to the job.

    Columns present in the template but absent from the job's dataset are
    silently skipped (reported in the ``skipped`` list of the response).
    """
    job = _get_job(job_id)

    # Read with size guard
    content = await file.read()
    if len(content) > _MAX_TEMPLATE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Le fichier YAML dépasse la taille maximale autorisée (1 Mo).",
        )

    # Parse — safe_load only, never yaml.load
    try:
        template = yaml.safe_load(content.decode("utf-8", errors="replace"))
    except yaml.YAMLError:
        raise HTTPException(
            status_code=422,
            detail="Le fichier YAML n'est pas un template Tablerreur valide.",
        )

    if not isinstance(template, dict):
        raise HTTPException(
            status_code=422,
            detail="Le fichier YAML n'est pas un template Tablerreur valide.",
        )

    # Minimal structural validation
    if "columns" not in template and "rules" not in template:
        raise HTTPException(
            status_code=422,
            detail="Le fichier YAML n'est pas un template Tablerreur valide.",
        )

    tpl_columns: dict = template.get("columns", {})
    if not isinstance(tpl_columns, dict):
        tpl_columns = {}

    applied: list[str] = []
    skipped: list[str] = []

    for col, col_cfg in tpl_columns.items():
        if not isinstance(col_cfg, dict):
            continue
        if col in job.columns:
            if col not in job.column_config:
                job.column_config[col] = {}
            for key, val in col_cfg.items():
                job.column_config[col][key] = val
            applied.append(col)
        else:
            skipped.append(col)

    job_manager.update(job)

    n_a = len(applied)
    n_s = len(skipped)
    if n_s == 0:
        msg = (
            f"Modèle importé : {n_a} colonne{'s' if n_a != 1 else ''} "
            f"configurée{'s' if n_a != 1 else ''}."
        )
    else:
        msg = (
            f"Modèle importé : {n_a} colonne{'s' if n_a != 1 else ''} "
            f"configurée{'s' if n_a != 1 else ''}, "
            f"{n_s} colonne{'s' if n_s != 1 else ''} ignorée{'s' if n_s != 1 else ''} "
            f"(absente{'s' if n_s != 1 else ''} du fichier)."
        )

    return {"applied": applied, "skipped": skipped, "message": msg}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_job(job_id: str) -> Job:
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Session introuvable ou expirée")
    return job


def _load_df(job: Job) -> pd.DataFrame:
    if job._df_path is None or not job._df_path.exists():
        raise HTTPException(status_code=422, detail="Données non disponibles")
    return pd.read_pickle(str(job._df_path))
