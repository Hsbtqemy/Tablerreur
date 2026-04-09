"""Tests for work exports available from the Correctifs step."""

from __future__ import annotations

import csv
import io

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from spreadsheet_qa.web.app import app  # noqa: E402

client = TestClient(app)


def _make_csv(columns: list[str], rows: list[list[str]]) -> bytes:
    lines = [";".join(columns)]
    for row in rows:
        lines.append(";".join(row))
    return "\n".join(lines).encode("utf-8")


def _upload_csv(columns: list[str], rows: list[list[str]]) -> str:
    csv_bytes = _make_csv(columns, rows)
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1"},
    )
    assert resp.status_code == 200
    return resp.json()["job_id"]


def _upload_and_validate() -> str:
    job_id = _upload_csv(
        ["langue", "annee"],
        [
            ["fra", "2024"],
            ["eng", "2023"],
            ["fra", "not_a_year"],
            ["deu", "2022"],
            ["ita", "2021"],
            ["spa", "2020"],
            ["por", "2019"],
            ["fra", "2018"],
            ["eng", "2017"],
        ],
    )
    resp = client.post(f"/api/jobs/{job_id}/validate")
    assert resp.status_code == 200
    return job_id


def _get_first_issue_id(job_id: str) -> str | None:
    resp = client.get(f"/api/jobs/{job_id}/problems?per_page=1")
    assert resp.status_code == 200
    problems = resp.json().get("problèmes", [])
    if not problems:
        return None
    return problems[0].get("issue_id")


def test_annotated_export_supports_touched_scope_before_validation():
    job_id = _upload_csv(
        ["titre", "annee"],
        [["Valeur initiale", "2024"], ["Autre valeur", "2023"]],
    )

    edit_resp = client.post(
        f"/api/jobs/{job_id}/edit-cell",
        json={"row": 0, "column": "titre", "value": "Valeur corrigée"},
    )
    assert edit_resp.status_code == 200

    export_resp = client.post(
        f"/api/jobs/{job_id}/exports/annotated",
        json={
            "scope": "touched",
            "format": "csv",
            "include_status_column": True,
            "include_visual_marks": False,
            "only_open": True,
        },
    )
    assert export_resp.status_code == 200
    assert "tableur_annote_touched" in export_resp.headers["content-disposition"]

    content = export_resp.content.decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(content), delimiter=";"))
    assert len(rows) == 1
    assert rows[0]["__tablerreur_ligne"] == "1"
    assert rows[0]["titre"] == "Valeur corrigée"
    assert rows[0]["annee"] == "2024"


def test_issues_report_applies_status_overrides_and_only_open_filter():
    job_id = _upload_and_validate()
    issue_id = _get_first_issue_id(job_id)
    if not issue_id:
        pytest.skip("Aucun problème détecté dans le jeu de test")

    status_resp = client.put(
        f"/api/jobs/{job_id}/issues/{issue_id}/status",
        json={"status": "IGNORED"},
    )
    assert status_resp.status_code == 200

    export_all_resp = client.post(
        f"/api/jobs/{job_id}/exports/issues-report",
        json={"format": "csv", "scope": "all", "only_open": False},
    )
    assert export_all_resp.status_code == 200
    rows_all = list(csv.DictReader(io.StringIO(export_all_resp.content.decode("utf-8")), delimiter=";"))
    assert any(row["statut"] == "IGNORED" for row in rows_all)

    export_open_resp = client.post(
        f"/api/jobs/{job_id}/exports/issues-report",
        json={"format": "csv", "scope": "all", "only_open": True},
    )
    assert export_open_resp.status_code == 200
    rows_open = list(csv.DictReader(io.StringIO(export_open_resp.content.decode("utf-8")), delimiter=";"))
    assert all(row["statut"] == "OPEN" for row in rows_open)
