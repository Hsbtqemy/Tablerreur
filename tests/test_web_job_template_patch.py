"""PATCH /api/jobs/{id}/template — modèle après création du job (étape Configurer)."""

from __future__ import annotations

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


def test_patch_template_overlay_updates_column_config():
    """Job créé en generic_default ; PATCH avec overlay NAKALA → colonnes NAKALA contraintes."""
    csv_bytes = _make_csv(
        ["nakala:title", "x"],
        [["t", "1"]],
    )
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    cfg0 = client.get(f"/api/jobs/{job_id}/column-config").json()["columns"]
    assert cfg0.get("nakala:title", {}).get("required") is not True

    r2 = client.patch(
        f"/api/jobs/{job_id}/template",
        json={"template_id": "generic_default", "overlay_id": "nakala_extended"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["overlay_id"] == "nakala_extended"

    cfg1 = client.get(f"/api/jobs/{job_id}/column-config").json()["columns"]
    assert cfg1.get("nakala:title", {}).get("required") is True


def test_patch_template_unknown_job():
    r = client.patch(
        "/api/jobs/job-inexistant-xyz/template",
        json={"template_id": "generic_default", "overlay_id": None},
    )
    assert r.status_code == 404


def test_column_config_user_overrides_reflects_saved_columns():
    """GET column-config expose user_overrides : True si job.column_config[col] non vide."""
    csv_bytes = _make_csv(["a", "b"], [["1", "2"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    d = client.get(f"/api/jobs/{job_id}/column-config").json()
    assert "user_overrides" in d
    assert d["user_overrides"]["a"] is False
    assert d["user_overrides"]["b"] is False
    r = client.put(
        f"/api/jobs/{job_id}/column-config",
        json={"columns": {"a": {"required": True}}},
    )
    assert r.status_code == 200
    d2 = client.get(f"/api/jobs/{job_id}/column-config").json()
    assert d2["user_overrides"]["a"] is True
    assert d2["user_overrides"]["b"] is False
