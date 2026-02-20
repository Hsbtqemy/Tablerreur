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
import pickle
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from spreadsheet_qa.core.dataset import DatasetLoader
from spreadsheet_qa.core.engine import ValidationEngine
from spreadsheet_qa.core.exporters import CSVExporter, IssuesCSVExporter, TXTReporter, XLSXExporter
from spreadsheet_qa.core.models import IssueStatus, Severity
from spreadsheet_qa.core.template_manager import TemplateManager
from spreadsheet_qa.core.text_utils import INVISIBLE_RE, UNICODE_SUSPECTS
from spreadsheet_qa.web.jobs import Job, JobState, ProblemRow, ValidationSummary, job_manager

app = FastAPI(
    title="Tablerreur API",
    description="API de contrôle qualité pour tableurs CSV/XLSX",
    version="0.1.0",
)

# Serve the static frontend files
_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


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
            "regex": _pick("regex", None),
            "min_length": _pick("min_length", None),
            "max_length": _pick("max_length", None),
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
    job = job_manager.create()
    job.state = JobState.LOADING
    job.filename = file.filename or "fichier"
    job.template_id = template_id
    job.overlay_id = overlay_id or None

    # Save upload
    suffix = Path(file.filename).suffix if file.filename else ".csv"
    upload_path = job.work_dir / f"input{suffix}"
    content = await file.read()
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
