"""Tests for /api/jobs/{id}/detect-format."""

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


def test_detect_format_endpoint_suggests_integer():
    csv_bytes = _make_csv(["entier"], [["1"], ["2"], ["3"], ["4"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    detect = client.post(
        f"/api/jobs/{job_id}/detect-format",
        json={"column": "entier"},
    )
    assert detect.status_code == 200, detect.text
    data = detect.json()
    assert data["detected"] is True
    assert data["content_type"] == "number"
    assert data["format_preset"] == "integer"


def test_detect_format_endpoint_suggests_positive_int_for_quantity():
    csv_bytes = _make_csv(["quantite"], [["1"], ["2"], ["3"], ["4"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    detect = client.post(
        f"/api/jobs/{job_id}/detect-format",
        json={"column": "quantite"},
    )
    assert detect.status_code == 200, detect.text
    data = detect.json()
    assert data["detected"] is True
    assert data["content_type"] == "number"
    assert data["format_preset"] == "positive_int"
