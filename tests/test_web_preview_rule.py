"""Tests for /api/jobs/{id}/preview-rule."""

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


def test_preview_rule_includes_content_type_validation():
    csv_bytes = _make_csv(["age"], [["10"], ["11"], ["abc"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    preview = client.post(
        f"/api/jobs/{job_id}/preview-rule",
        json={"column": "age", "config": {"content_type": "integer"}},
    )
    assert preview.status_code == 200, preview.text
    data = preview.json()

    assert data["total_fail"] == 1
    assert any("entier" in item["message"].lower() for item in data["sample_fail"])


def test_preview_rule_includes_unique_constraint():
    csv_bytes = _make_csv(["id"], [["A1"], ["A1"], ["A2"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    preview = client.post(
        f"/api/jobs/{job_id}/preview-rule",
        json={"column": "id", "config": {"unique": True}},
    )
    assert preview.status_code == 200, preview.text
    data = preview.json()

    assert data["total_fail"] == 1
    assert any("duplicate" in item["message"].lower() for item in data["sample_fail"])
