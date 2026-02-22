"""Tests for issue status management endpoints.

Covers:
  - PUT /api/jobs/{job_id}/issues/{issue_id}/status
  - PUT /api/jobs/{job_id}/issues/bulk-status
  - Statut apparaît dans GET /problems
  - Filtre par statut dans GET /problems
  - Erreurs 404 / 422
"""

from __future__ import annotations

import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from spreadsheet_qa.web.app import app  # noqa: E402

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_csv(columns: list[str], rows: list[list[str]]) -> bytes:
    lines = [";".join(columns)]
    for row in rows:
        lines.append(";".join(row))
    return "\n".join(lines).encode("utf-8")


def _upload_and_validate() -> str:
    """Upload a CSV, validate it, and return the job_id."""
    # CSV with mixed data types to trigger generic.soft_typing
    csv_bytes = _make_csv(
        ["langue", "annee"],
        [["fra", "2024"], ["eng", "2023"], ["fra", "not_a_year"],
         ["deu", "2022"], ["ita", "2021"], ["spa", "2020"],
         ["por", "2019"], ["fra", "2018"], ["eng", "2017"]],
    )
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1"},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    # Validate
    resp2 = client.post(f"/api/jobs/{job_id}/validate")
    assert resp2.status_code == 200
    return job_id


def _get_first_issue_id(job_id: str) -> str | None:
    """Return the issue_id of the first open problem, or None."""
    resp = client.get(f"/api/jobs/{job_id}/problems?per_page=1")
    assert resp.status_code == 200
    probs = resp.json().get("problèmes", [])
    if probs:
        return probs[0].get("issue_id")
    return None


# ---------------------------------------------------------------------------
# Tests — statut individuel
# ---------------------------------------------------------------------------


def test_ignore_issue():
    job_id = _upload_and_validate()
    issue_id = _get_first_issue_id(job_id)
    if not issue_id:
        pytest.skip("Aucun problème détecté dans le fichier de test")

    resp = client.put(
        f"/api/jobs/{job_id}/issues/{issue_id}/status",
        json={"status": "IGNORED"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["status"] == "IGNORED"


def test_except_issue():
    job_id = _upload_and_validate()
    issue_id = _get_first_issue_id(job_id)
    if not issue_id:
        pytest.skip("Aucun problème détecté dans le fichier de test")

    resp = client.put(
        f"/api/jobs/{job_id}/issues/{issue_id}/status",
        json={"status": "EXCEPTED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "EXCEPTED"


def test_reopen_issue():
    job_id = _upload_and_validate()
    issue_id = _get_first_issue_id(job_id)
    if not issue_id:
        pytest.skip("Aucun problème détecté dans le fichier de test")

    # Ignore first
    client.put(
        f"/api/jobs/{job_id}/issues/{issue_id}/status",
        json={"status": "IGNORED"},
    )
    # Reopen
    resp = client.put(
        f"/api/jobs/{job_id}/issues/{issue_id}/status",
        json={"status": "OPEN"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "OPEN"


def test_status_appears_in_problems_response():
    job_id = _upload_and_validate()
    issue_id = _get_first_issue_id(job_id)
    if not issue_id:
        pytest.skip("Aucun problème détecté dans le fichier de test")

    client.put(
        f"/api/jobs/{job_id}/issues/{issue_id}/status",
        json={"status": "IGNORED"},
    )
    # The ignored issue should now appear with statut=IGNORED
    resp = client.get(f"/api/jobs/{job_id}/problems?per_page=50")
    assert resp.status_code == 200
    probs = resp.json()["problèmes"]
    found = next((p for p in probs if p["issue_id"] == issue_id), None)
    assert found is not None
    assert found["statut"] == "IGNORED"


def test_filter_by_status_open():
    job_id = _upload_and_validate()
    issue_id = _get_first_issue_id(job_id)
    if not issue_id:
        pytest.skip("Aucun problème détecté dans le fichier de test")

    client.put(
        f"/api/jobs/{job_id}/issues/{issue_id}/status",
        json={"status": "IGNORED"},
    )
    # Filter to OPEN only — ignored issue should not appear
    resp = client.get(f"/api/jobs/{job_id}/problems?status=OPEN&per_page=50")
    assert resp.status_code == 200
    probs = resp.json()["problèmes"]
    assert all(p["statut"] == "OPEN" for p in probs)
    assert not any(p["issue_id"] == issue_id for p in probs)


def test_filter_by_status_ignored():
    job_id = _upload_and_validate()
    issue_id = _get_first_issue_id(job_id)
    if not issue_id:
        pytest.skip("Aucun problème détecté dans le fichier de test")

    client.put(
        f"/api/jobs/{job_id}/issues/{issue_id}/status",
        json={"status": "IGNORED"},
    )
    resp = client.get(f"/api/jobs/{job_id}/problems?status=IGNORED&per_page=50")
    assert resp.status_code == 200
    probs = resp.json()["problèmes"]
    assert len(probs) >= 1
    assert all(p["statut"] == "IGNORED" for p in probs)


# ---------------------------------------------------------------------------
# Tests — statut en masse
# ---------------------------------------------------------------------------


def test_bulk_ignore():
    job_id = _upload_and_validate()
    resp = client.get(f"/api/jobs/{job_id}/problems?per_page=3")
    probs = resp.json().get("problèmes", [])
    ids = [p["issue_id"] for p in probs if p.get("issue_id")]
    if not ids:
        pytest.skip("Aucun problème détecté")

    resp2 = client.put(
        f"/api/jobs/{job_id}/issues/bulk-status",
        json={"issue_ids": ids, "status": "IGNORED"},
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["ok"] is True
    assert data["changed"] == len(ids)


# ---------------------------------------------------------------------------
# Tests — erreurs
# ---------------------------------------------------------------------------


def test_unknown_issue_returns_404():
    job_id = _upload_and_validate()
    resp = client.put(
        f"/api/jobs/{job_id}/issues/nonexistent-issue-id/status",
        json={"status": "IGNORED"},
    )
    assert resp.status_code == 404


def test_unknown_job_returns_404():
    resp = client.put(
        "/api/jobs/nonexistent-job/issues/someid/status",
        json={"status": "IGNORED"},
    )
    assert resp.status_code == 404


def test_invalid_status_returns_422():
    job_id = _upload_and_validate()
    issue_id = _get_first_issue_id(job_id)
    if not issue_id:
        pytest.skip("Aucun problème détecté")

    resp = client.put(
        f"/api/jobs/{job_id}/issues/{issue_id}/status",
        json={"status": "BLABLA"},
    )
    assert resp.status_code == 422
