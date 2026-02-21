"""Tablerreur Web App — FastAPI backend.

Workflow:
  POST /api/jobs            → upload file, create job → job_id
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

from spreadsheet_qa.core.dataset import DatasetLoader
from spreadsheet_qa.core.engine import ValidationEngine
from spreadsheet_qa.core.exporters import CSVExporter, IssuesCSVExporter, TXTReporter, XLSXExporter
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
_ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
# Les navigateurs et outils envoient parfois "application/octet-stream" pour
# les fichiers binaires — on accepte ce type générique et on se fie à l'extension.
_ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",
    "binary/octet-stream",
}

_logger = logging.getLogger(__name__)

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

# Serve the static frontend files
_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


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
    for col in job.columns:
        tpl = tpl_columns.get(col, {})
        user = job.column_config.get(col, {})

        def _pick(key: str, default):
            # User override wins if set, else template, else default
            if key in user and user[key] is not None:
                return user[key]
            v = tpl.get(key)
            if v is not None and v != [] and v != "":
                return v
            return default

        result[col] = {
            "content_type": _pick("content_type", None),
            "unique": _pick("unique", False),
            "multiline_ok": _pick("multiline_ok", False),
            "allowed_values": _pick("allowed_values", None),
            "allowed_values_locked": _pick("allowed_values_locked", False),
            "regex": _pick("regex", None),
            "min_length": _pick("min_length", None),
            "max_length": _pick("max_length", None),
            "yes_no_true_values": _pick("yes_no_true_values", None),
            "yes_no_false_values": _pick("yes_no_false_values", None),
            "detect_rare_values": _pick("detect_rare_values", False),
            "rare_threshold": _pick("rare_threshold", 1),
            "rare_min_total": _pick("rare_min_total", 10),
        }

    return {"columns": result}


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
    from spreadsheet_qa.core.rules.required import RequiredRule
    from spreadsheet_qa.core.rules.soft_typing import SoftTypingRule
    from spreadsheet_qa.core.rules.regex_rule import RegexRule
    from spreadsheet_qa.core.rules.allowed_values import AllowedValuesRule
    from spreadsheet_qa.core.rules.length import LengthRule
    from spreadsheet_qa.core.rules.forbidden_chars import ForbiddenCharsRule
    from spreadsheet_qa.core.rules.case_rule import CaseRule
    from spreadsheet_qa.core.rules.rare_values import RareValuesRule

    # For SoftTypingRule use a lower min_count so it fires on small datasets
    preview_config = {"min_count": 5, **config}

    rules = [
        RequiredRule(), SoftTypingRule(), RegexRule(),
        AllowedValuesRule(), LengthRule(), ForbiddenCharsRule(),
        CaseRule(), RareValuesRule(),
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


# ---------------------------------------------------------------------------
# Job creation (upload)
# ---------------------------------------------------------------------------


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    header_row: int = Form(1),
    delimiter: str = Form(""),
    encoding: str = Form(""),
    template_id: str = Form("generic_default"),
    overlay_id: str = Form(""),
):
    """Upload a file and create a new validation job."""
    # --- Validation du type de fichier (avant création du job) ---
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Type de fichier non pris en charge. Formats acceptés : CSV, XLSX, XLS.",
        )
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct and ct not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Type de fichier non pris en charge. Formats acceptés : CSV, XLSX, XLS.",
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
        df, meta = loader.load(
            path=upload_path,
            header_row=max(0, header_row - 1),
            encoding_hint=encoding or None,
            delimiter_hint=delimiter or None,
        )
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

    cells_fixed = 0
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
                df.at[row_idx, col] = fixed
                cells_fixed += 1

    job.cells_fixed = cells_fixed
    # Persist updated DataFrame
    df.to_pickle(str(job._df_path))
    job.state = JobState.PENDING
    job_manager.update(job)

    return {"cells_fixed": cells_fixed, "state": job.state.value}


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
        mgr = TemplateManager()
        config = mgr.compile_config(
            generic_id=job.template_id,
            overlay_id=job.overlay_id,
            column_names=list(df.columns),
            nakala_client=_nakala_client,
        )
        # Merge user column overrides from the configure step
        if job.column_config:
            config_cols = config.setdefault("columns", {})
            for col, user_overrides in job.column_config.items():
                if col not in config_cols:
                    config_cols[col] = {}
                for key, val in user_overrides.items():
                    if val is not None:
                        config_cols[col][key] = val
        engine = ValidationEngine()
        issues = engine.validate(df, config=config)
    except Exception as exc:
        job.state = JobState.ERROR
        job.error_msg = str(exc)
        job_manager.update(job)
        raise HTTPException(status_code=500, detail=str(exc))

    # Build summary
    counts = {
        Severity.ERROR: 0,
        Severity.WARNING: 0,
        Severity.SUSPICION: 0,
    }
    for issue in issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1

    job.summary = ValidationSummary(
        errors=counts[Severity.ERROR],
        warnings=counts[Severity.WARNING],
        suspicions=counts[Severity.SUSPICION],
        total=len(issues),
    )

    # Store problems
    job.problems = [
        ProblemRow(
            severity=issue.severity.value,
            status=issue.status.value,
            column=issue.col,
            row=issue.row + 1,
            message=issue.message,
            suggestion=str(issue.suggestion) if issue.suggestion is not None else "",
        )
        for issue in issues
    ]

    # Generate downloadable outputs
    _generate_outputs(job, df, issues)

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
    }


def _generate_outputs(job: Job, df: pd.DataFrame, issues: list) -> None:
    """Pre-generate all downloadable files."""
    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out = job.work_dir / "exports"
    out.mkdir(exist_ok=True)

    # Find a DatasetMeta-like object if available
    try:
        from spreadsheet_qa.core.models import DatasetMeta
        meta = DatasetMeta(
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
    except Exception:
        meta = None

    try:
        XLSXExporter().export(df, out / "nettoyé.xlsx")
    except Exception:
        pass
    try:
        CSVExporter().export(df, out / "nettoyé.csv")
    except Exception:
        pass
    try:
        TXTReporter().export(issues, out / "rapport.txt", meta=meta)
    except Exception:
        pass
    try:
        IssuesCSVExporter().export(issues, out / "problèmes.csv", meta=meta)
    except Exception:
        pass


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
):
    """Return a paginated, filtered list of problems for a job."""
    job = _get_job(job_id)
    problems = job.problems

    # Filter
    if severity:
        problems = [p for p in problems if p.severity == severity]
    if column:
        problems = [p for p in problems if p.column == column]

    total = len(problems)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = problems[start:end]

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "problèmes": [
            {
                "sévérité": p.severity,
                "statut": p.status,
                "colonne": p.column,
                "ligne": p.row,
                "message": p.message,
                "suggestion": p.suggestion,
            }
            for p in page_items
        ],
    }


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

    return {"values": values, "count": len(values), "source": "NAKALA API"}


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
