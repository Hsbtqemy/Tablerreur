"""Mapala routes — endpoints FastAPI pour le mapping de tableurs.

Endpoints :
  POST /api/mapala/upload                  → upload template + source, crée un job
  POST /api/mapala/preview                 → aperçu colonnes + premières lignes
  POST /api/mapala/build                   → construit le fichier mappé
  GET  /api/mapala/jobs/{job_id}/download  → télécharge le résultat
  POST /api/mapala/jobs/{job_id}/validate  → crée un job Tablerreur depuis le résultat
"""

from __future__ import annotations

import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from spreadsheet_qa.core.mapala import list_sheets, load_sheet, save_mapala_output
from spreadsheet_qa.web.jobs import TTL_SECONDS, JobState, job_manager


# ---------------------------------------------------------------------------
# MapalaJob dataclass
# ---------------------------------------------------------------------------


@dataclass
class MapalaJob:
    id: str
    template_path: Path | None = None
    source_path: Path | None = None
    result_path: Path | None = None
    template_filename: str = ""
    source_filename: str = ""
    work_dir: Path = field(default_factory=Path)
    created_at: float = field(default_factory=time.time)
    rows_mapped: int = 0
    columns_mapped: int = 0


# ---------------------------------------------------------------------------
# Job store en mémoire
# ---------------------------------------------------------------------------

_mapala_jobs: dict[str, MapalaJob] = {}
_mapala_lock = threading.Lock()


def _create_mapala_job() -> MapalaJob:
    job_id = str(uuid.uuid4())
    work_dir = Path(tempfile.mkdtemp(prefix=f"mapala_{job_id}_"))
    job = MapalaJob(id=job_id, work_dir=work_dir)
    with _mapala_lock:
        _mapala_jobs[job_id] = job
    return job


def _get_mapala_job(job_id: str) -> MapalaJob:
    with _mapala_lock:
        job = _mapala_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job Mapala introuvable: {job_id}")
    if time.time() - job.created_at > TTL_SECONDS:
        with _mapala_lock:
            _mapala_jobs.pop(job_id, None)
        raise HTTPException(status_code=404, detail="Job Mapala expiré")
    return job


def _cleanup_mapala_jobs() -> None:
    now = time.time()
    expired = []
    with _mapala_lock:
        for job_id, job in list(_mapala_jobs.items()):
            if now - job.created_at > TTL_SECONDS:
                expired.append((job_id, job))
    for job_id, job in expired:
        with _mapala_lock:
            _mapala_jobs.pop(job_id, None)
        if job.work_dir.exists():
            shutil.rmtree(job.work_dir, ignore_errors=True)


def _start_mapala_cleanup() -> None:
    def _loop() -> None:
        while True:
            time.sleep(300)
            _cleanup_mapala_jobs()

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


_start_mapala_cleanup()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/mapala")


# ---------------------------------------------------------------------------
# POST /api/mapala/upload
# ---------------------------------------------------------------------------


@router.post("/upload")
async def mapala_upload(
    template_file: UploadFile = File(...),
    source_file: UploadFile = File(...),
):
    """Upload template + source, retourne les listes de feuilles disponibles."""
    job = _create_mapala_job()

    # Sauvegarde du template
    template_ext = Path(template_file.filename or "template.xlsx").suffix or ".xlsx"
    template_path = job.work_dir / f"template{template_ext}"
    template_path.write_bytes(await template_file.read())
    job.template_path = template_path
    job.template_filename = template_file.filename or ""

    # Sauvegarde de la source
    source_ext = Path(source_file.filename or "source.xlsx").suffix or ".xlsx"
    source_path = job.work_dir / f"source{source_ext}"
    source_path.write_bytes(await source_file.read())
    job.source_path = source_path
    job.source_filename = source_file.filename or ""

    try:
        template_sheets = list_sheets(template_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lecture template : {e}")

    try:
        source_sheets = list_sheets(source_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lecture source : {e}")

    with _mapala_lock:
        _mapala_jobs[job.id] = job

    return {
        "job_id": job.id,
        "template_sheets": template_sheets,
        "source_sheets": source_sheets,
        "template_filename": job.template_filename,
        "source_filename": job.source_filename,
    }


# ---------------------------------------------------------------------------
# POST /api/mapala/preview
# ---------------------------------------------------------------------------


@router.post("/preview")
async def mapala_preview(body: dict):
    """Charge les deux feuilles et retourne un aperçu des colonnes + données."""
    job_id = str(body.get("job_id", ""))
    job = _get_mapala_job(job_id)

    template_sheet = body.get("template_sheet") or None
    source_sheet = body.get("source_sheet") or None
    rows = int(body.get("rows", 30))

    try:
        df_template = load_sheet(job.template_path, template_sheet)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lecture template : {e}")

    try:
        df_source = load_sheet(job.source_path, source_sheet)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lecture source : {e}")

    def _rows(df: pd.DataFrame, n: int) -> list[list[str]]:
        result = []
        for _, row in df.head(n).iterrows():
            result.append(["" if pd.isna(v) else str(v) for v in row])
        return result

    return {
        "template_columns": list(df_template.columns),
        "source_columns": list(df_source.columns),
        "template_preview": _rows(df_template, rows),
        "source_preview": _rows(df_source, rows),
    }


# ---------------------------------------------------------------------------
# POST /api/mapala/build
# ---------------------------------------------------------------------------


@router.post("/build")
async def mapala_build(body: dict):
    """Construit le fichier de sortie mappé depuis la config de mapping."""
    job_id = str(body.get("job_id", ""))
    job = _get_mapala_job(job_id)

    template_sheet = body.get("template_sheet") or None
    source_sheet = body.get("source_sheet") or None
    mappings: list[dict] = body.get("mappings", [])
    output_format = str(body.get("output_format", "xlsx")).lower().strip(".")
    if output_format not in ("xlsx", "ods", "csv"):
        output_format = "xlsx"

    try:
        df_template = load_sheet(job.template_path, template_sheet)
        df_source = load_sheet(job.source_path, source_sheet)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur lecture fichiers : {e}")

    template_cols = list(df_template.columns)
    n = len(df_source)

    # Construction ligne par ligne
    output_data: dict[str, list] = {col: [""] * n for col in template_cols}

    for m in mappings:
        template_col = m.get("template_col", "")
        if not template_col or template_col not in output_data:
            continue

        if "value" in m:
            # Valeur fixe
            output_data[template_col] = [str(m["value"])] * n

        elif source_cols_list := m.get("source_cols"):
            # Mode concaténation
            separator = str(m.get("separator", " "))
            prefixes: list[str] = m.get("prefix") or [""] * len(source_cols_list)
            col_data: list[tuple[str, list[str]]] = []
            for i, src_col in enumerate(source_cols_list):
                prefix = prefixes[i] if i < len(prefixes) else ""
                if src_col in df_source.columns:
                    vals = df_source[src_col].fillna("").astype(str).tolist()
                else:
                    vals = [""] * n
                col_data.append((prefix, vals))

            result_col: list[str] = []
            for row_i in range(n):
                parts = []
                for pfx, vals in col_data:
                    v = vals[row_i]
                    if v.strip():
                        parts.append(f"{pfx}{v}" if pfx else v)
                result_col.append(separator.join(parts))
            output_data[template_col] = result_col

        elif source_col := m.get("source_col"):
            # Mode simple
            if source_col in df_source.columns:
                output_data[template_col] = df_source[source_col].fillna("").astype(str).tolist()

    df_result = pd.DataFrame(output_data)

    mapped_cols = sum(
        1 for m in mappings
        if m.get("source_col") or m.get("source_cols") or "value" in m
    )

    # Sauvegarde du résultat
    result_path = job.work_dir / f"resultat.{output_format}"
    try:
        save_mapala_output(result_path, {"Résultat": df_result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur sauvegarde : {e}")

    job.result_path = result_path
    job.rows_mapped = n
    job.columns_mapped = mapped_cols

    with _mapala_lock:
        _mapala_jobs[job.id] = job

    return {
        "job_id": job.id,
        "rows_mapped": n,
        "columns_mapped": mapped_cols,
    }


# ---------------------------------------------------------------------------
# GET /api/mapala/jobs/{job_id}/download
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/download")
async def mapala_download(job_id: str):
    """Retourne le fichier résultat en téléchargement."""
    job = _get_mapala_job(job_id)
    if not job.result_path or not job.result_path.exists():
        raise HTTPException(status_code=404, detail="Résultat non disponible")

    filename = f"mapala_resultat{job.result_path.suffix}"
    return FileResponse(
        path=str(job.result_path),
        filename=filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# POST /api/mapala/jobs/{job_id}/validate
# ---------------------------------------------------------------------------


@router.post("/jobs/{job_id}/validate")
async def mapala_validate(job_id: str):
    """Crée un job Tablerreur depuis le résultat Mapala (pont mapper → valider)."""
    job = _get_mapala_job(job_id)
    if not job.result_path or not job.result_path.exists():
        raise HTTPException(status_code=404, detail="Résultat Mapala non disponible")

    # Création d'un job Tablerreur
    tablerreur_job = job_manager.create()

    # Copie du fichier résultat dans le répertoire Tablerreur
    dest = tablerreur_job.work_dir / job.result_path.name
    shutil.copy2(job.result_path, dest)
    tablerreur_job.upload_path = dest
    tablerreur_job.filename = dest.name

    # Chargement du DataFrame
    try:
        df = load_sheet(dest, sheet_name="Résultat")
    except Exception:
        try:
            df = load_sheet(dest)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lecture résultat : {e}")

    df = df.astype(str)
    tablerreur_job.rows = len(df)
    tablerreur_job.cols = len(df.columns)
    tablerreur_job.columns = list(df.columns)

    df_path = tablerreur_job.work_dir / "df.pkl"
    df.to_pickle(str(df_path))
    tablerreur_job._df_path = df_path
    tablerreur_job.state = JobState.LOADING

    job_manager.update(tablerreur_job)

    return {"tablerreur_job_id": tablerreur_job.id}
