"""Job manager for the Tablerreur web app.

Each upload creates a temporary job. Jobs are stored in memory (dict) and
their associated files live in a system temp directory. Jobs expire after
``TTL_SECONDS`` and are cleaned up automatically.
"""

from __future__ import annotations

import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


TTL_SECONDS = 3600  # 1 hour


class JobState(str, Enum):
    PENDING = "en_attente"
    LOADING = "chargement"
    FIXING = "correction"
    VALIDATING = "validation"
    DONE = "terminé"
    ERROR = "erreur"


@dataclass
class ValidationSummary:
    errors: int = 0
    warnings: int = 0
    suspicions: int = 0
    total: int = 0


@dataclass
class ProblemRow:
    severity: str
    status: str
    column: str
    row: int
    message: str
    suggestion: str


@dataclass
class Job:
    id: str
    state: JobState = JobState.PENDING
    filename: str = ""
    error_msg: str = ""
    # Paths
    work_dir: Path = field(default_factory=Path)
    upload_path: Path | None = None
    # Dataset info
    rows: int = 0
    cols: int = 0
    columns: list[str] = field(default_factory=list)
    # Template
    template_id: str = "generic_default"
    overlay_id: str | None = None
    # Per-column config set in the configure step (overrides template defaults)
    column_config: dict = field(default_factory=dict)
    # Fix options applied
    fixes_applied: dict[str, bool] = field(default_factory=dict)
    cells_fixed: int = 0
    # Validation results
    summary: ValidationSummary = field(default_factory=ValidationSummary)
    problems: list[ProblemRow] = field(default_factory=list)
    # Expiry
    created_at: float = field(default_factory=time.time)
    # DataFrame stored as pickle for downstream steps
    _df_path: Path | None = None


class JobManager:
    """Thread-safe in-memory job store with automatic expiry."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._start_cleanup_thread()

    def create(self) -> Job:
        job_id = str(uuid.uuid4())
        work_dir = Path(tempfile.mkdtemp(prefix=f"tablerreur_{job_id}_"))
        job = Job(id=job_id, work_dir=work_dir)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.id] = job

    def delete(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.pop(job_id, None)
        if job and job.work_dir.exists():
            shutil.rmtree(job.work_dir, ignore_errors=True)

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = []
        with self._lock:
            for job_id, job in self._jobs.items():
                if now - job.created_at > TTL_SECONDS:
                    expired.append(job_id)
        for job_id in expired:
            self.delete(job_id)

    def _start_cleanup_thread(self) -> None:
        def _loop() -> None:
            while True:
                time.sleep(300)  # check every 5 minutes
                self._cleanup_expired()

        t = threading.Thread(target=_loop, daemon=True)
        t.start()


# Singleton used by FastAPI routes
job_manager = JobManager()
