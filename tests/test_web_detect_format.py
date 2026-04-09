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
    assert data["candidates"][0]["format_preset"] == "integer"


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
    assert data["candidates"][0]["format_preset"] == "positive_int"


def test_detect_format_endpoint_suggests_yes_no_boolean():
    csv_bytes = _make_csv(["statut"], [["oui"], ["non"], ["oui"], ["non"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    detect = client.post(
        f"/api/jobs/{job_id}/detect-format",
        json={"column": "statut"},
    )
    assert detect.status_code == 200, detect.text
    data = detect.json()
    assert data["detected"] is True
    assert data["content_type"] == "boolean"
    assert data["format_preset"] == "yes_no"
    assert data["candidates"][0]["format_preset"] == "yes_no"


def test_detect_format_endpoint_returns_candidates_for_ambiguous_years():
    csv_bytes = _make_csv(["code"], [["2020"], ["2021"], ["2022"], ["2023"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    detect = client.post(
        f"/api/jobs/{job_id}/detect-format",
        json={"column": "code"},
    )
    assert detect.status_code == 200, detect.text
    data = detect.json()
    assert data["detected"] is False
    assert len(data["candidates"]) >= 2
    assert data["candidates"][0]["content_type"] == "date"
    assert any(candidate["content_type"] == "number" for candidate in data["candidates"])


@pytest.mark.parametrize(
    ("column_name", "rows", "expected_type", "expected_preset"),
    [
        ("doi_reference", [["10.1234/alpha"], ["10.5281/zenodo.42"], ["10.1000/test"]], "identifier", "doi"),
        ("latitude", [["48.8566"], ["43.2965"], ["-21.1151"]], "number", "latitude"),
        ("date_publication", [["2024-01"], ["2024-02"], ["2025-03"]], "date", "w3cdtf"),
        ("date_publication", [["2024-01-15"], ["2024-02-01"], ["2025-03-31"]], "date", "iso_date"),
        ("statut", [["actif"], ["inactif"], ["actif"], ["inactif"]], "boolean", "yes_no"),
    ],
)
def test_detect_format_endpoint_real_world_presets(column_name, rows, expected_type, expected_preset):
    csv_bytes = _make_csv([column_name], rows)
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    detect = client.post(
        f"/api/jobs/{job_id}/detect-format",
        json={"column": column_name},
    )
    assert detect.status_code == 200, detect.text
    data = detect.json()
    assert data["detected"] is True
    assert data["content_type"] == expected_type
    assert data["format_preset"] == expected_preset
    assert data["candidates"][0]["content_type"] == expected_type
    assert data["candidates"][0]["format_preset"] == expected_preset
