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
    csv_bytes = _make_csv(["age"], [["10"], ["11"], ["1.5"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    preview = client.post(
        f"/api/jobs/{job_id}/preview-rule",
        json={"column": "age", "config": {"content_type": "number", "format_preset": "integer"}},
    )
    assert preview.status_code == 200, preview.text
    data = preview.json()

    assert data["total_fail"] == 1
    assert any(item["value"] == "1.5" for item in data["sample_fail"])


def test_preview_rule_keeps_legacy_integer_alias_compatible():
    csv_bytes = _make_csv(["age"], [["10"], ["11"], ["1.5"]])
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
    assert any(item["value"] == "1.5" for item in data["sample_fail"])


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


@pytest.mark.parametrize(
    ("column_name", "rows", "config", "valid_value", "invalid_value"),
    [
        ("periode", [["01/2024"], ["13/2024"]], {"content_type": "date", "format_preset": "month_year"}, "01/2024", "13/2024"),
        ("ref_handle", [["20.500.12345/abc"], ["10.1234/doi"]], {"content_type": "identifier", "format_preset": "handle"}, "20.500.12345/abc", "10.1234/doi"),
        ("isbn_mixte", [["9781234567890"], ["012345678X"], ["pas-un-isbn"]], {"content_type": "identifier", "format_preset": "isbn"}, "9781234567890", "pas-un-isbn"),
        ("montant", [["42"], ["3.14"], ["abc"]], {"content_type": "number", "format_preset": "integer_or_decimal"}, "42", "abc"),
    ],
)
def test_preview_rule_supports_new_presets(column_name, rows, config, valid_value, invalid_value):
    csv_bytes = _make_csv([column_name], rows)
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    preview = client.post(
        f"/api/jobs/{job_id}/preview-rule",
        json={"column": column_name, "config": config},
    )
    assert preview.status_code == 200, preview.text
    data = preview.json()

    assert any(value == valid_value for value in data["sample_ok"])
    assert any(item["value"] == invalid_value for item in data["sample_fail"])
