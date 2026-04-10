"""PATCH /api/jobs/{id}/template — modèle après création du job (étape Configurer)."""

from __future__ import annotations

import io

import pytest
import yaml

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from spreadsheet_qa.web.app import (  # noqa: E402
    _canonicalize_format_config,
    _has_manual_format_override,
    app,
)

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
    """GET column-config expose user_overrides et user_format_overrides."""
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
    assert "user_format_overrides" in d
    assert d["user_overrides"]["a"] is False
    assert d["user_overrides"]["b"] is False
    assert d["user_format_overrides"]["a"] is False
    assert d["user_format_overrides"]["b"] is False
    r = client.put(
        f"/api/jobs/{job_id}/column-config",
        json={"columns": {"a": {"required": True}}},
    )
    assert r.status_code == 200
    d2 = client.get(f"/api/jobs/{job_id}/column-config").json()
    assert d2["user_overrides"]["a"] is True
    assert d2["user_overrides"]["b"] is False
    assert d2["user_format_overrides"]["a"] is False
    assert d2["user_format_overrides"]["b"] is False

    r2 = client.put(
        f"/api/jobs/{job_id}/column-config",
        json={"columns": {"a": {"content_type": "number", "format_preset": "integer"}}},
    )
    assert r2.status_code == 200
    d3 = client.get(f"/api/jobs/{job_id}/column-config").json()
    assert d3["user_format_overrides"]["a"] is True


def test_canonicalize_format_config_maps_legacy_aliases():
    assert _canonicalize_format_config({"content_type": "integer"}) == (
        "number",
        "integer",
        None,
        None,
        None,
    )
    assert _canonicalize_format_config({"content_type": "email", "regex": r"^.+$"}) == (
        "address",
        "custom",
        r"^.+$",
        None,
        None,
    )


def test_has_manual_format_override_ignores_legacy_integer_alias_equivalence():
    assert (
        _has_manual_format_override(
            {"content_type": "integer"},
            {"content_type": "number", "format_preset": "integer"},
        )
        is False
    )


def test_get_column_config_canonicalizes_legacy_integer_alias():
    csv_bytes = _make_csv(["annee"], [["2024"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    saved = client.put(
        f"/api/jobs/{job_id}/column-config",
        json={"columns": {"annee": {"content_type": "integer"}}},
    )
    assert saved.status_code == 200

    data = client.get(f"/api/jobs/{job_id}/column-config").json()
    assert data["columns"]["annee"]["content_type"] == "number"
    assert data["columns"]["annee"]["format_preset"] == "integer"


def test_validate_keeps_legacy_integer_alias_effective():
    csv_bytes = _make_csv(["annee"], [["2024"], ["1.5"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    saved = client.put(
        f"/api/jobs/{job_id}/column-config",
        json={"columns": {"annee": {"content_type": "integer"}}},
    )
    assert saved.status_code == 200

    validation = client.post(f"/api/jobs/{job_id}/validate")
    assert validation.status_code == 200
    data = validation.json()
    summary = next(value for value in data.values() if isinstance(value, dict) and "total" in value)
    assert summary["total"] >= 1


def test_export_template_canonicalizes_legacy_integer_alias():
    csv_bytes = _make_csv(["annee"], [["2024"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    saved = client.put(
        f"/api/jobs/{job_id}/column-config",
        json={"columns": {"annee": {"content_type": "integer"}}},
    )
    assert saved.status_code == 200

    exported = client.get(f"/api/jobs/{job_id}/export-template")
    assert exported.status_code == 200
    parsed = yaml.safe_load(exported.text)

    assert parsed["columns"]["annee"]["content_type"] == "number"
    assert parsed["columns"]["annee"]["format_preset"] == "integer"


def test_import_template_canonicalizes_legacy_integer_alias():
    csv_bytes = _make_csv(["annee"], [["2024"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": ""},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    template = yaml.safe_dump(
        {
            "name": "Legacy integer alias",
            "type": "generic",
            "columns": {
                "annee": {
                    "content_type": "integer",
                }
            },
        },
        allow_unicode=True,
        sort_keys=False,
    ).encode("utf-8")

    imported = client.post(
        f"/api/jobs/{job_id}/import-template",
        files={"file": ("template.yml", io.BytesIO(template), "application/x-yaml")},
    )
    assert imported.status_code == 200

    data = client.get(f"/api/jobs/{job_id}/column-config").json()
    assert data["columns"]["annee"]["content_type"] == "number"
    assert data["columns"]["annee"]["format_preset"] == "integer"


def test_template_metadata_exposes_nakala_columns_and_groups():
    csv_bytes = _make_csv(["title"], [["Mon titre"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": "nakala_extended"},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    meta = client.get(f"/api/jobs/{job_id}/template-metadata")
    assert meta.status_code == 200, meta.text
    data = meta.json()

    assert data["overlay_id"] == "nakala_extended"
    assert "nakala:title" in data["columns"]
    assert data["columns"]["nakala:creator"]["special_values"] == ["Anonyme"]
    assert data["columns"]["nakala:creator"]["rule_overrides"]["nakala.created_format"]["enabled"] is False
    assert "nakala:title_*" in data["column_groups"]
    assert "nakala:title" in data["required_columns"]
    assert "dcterms:language" in data["recommended_columns"]


def test_template_metadata_can_seed_alias_column_with_hidden_nakala_fields():
    csv_bytes = _make_csv(["creator_name"], [["Anonyme"], ["Dupont Jean"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": "generic_default", "overlay_id": "nakala_baseline"},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    meta = client.get(f"/api/jobs/{job_id}/template-metadata")
    assert meta.status_code == 200, meta.text
    creator_cfg = meta.json()["columns"]["nakala:creator"]

    saved = client.put(
        f"/api/jobs/{job_id}/column-config",
        json={"columns": {"creator_name": creator_cfg}},
    )
    assert saved.status_code == 200

    validation = client.post(f"/api/jobs/{job_id}/validate")
    assert validation.status_code == 200

    problems = client.get(
        f"/api/jobs/{job_id}/problems",
        params={"column": "creator_name", "per_page": 50},
    )
    assert problems.status_code == 200, problems.text
    rows = [entry["ligne"] for entry in problems.json()["problèmes"]]
    assert 1 not in rows
    assert 2 in rows
