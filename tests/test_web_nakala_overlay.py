"""Tests for NAKALA overlay template merging.

Covers:
  - POST /api/jobs with template_id=generic_default + overlay_id=nakala_extended
    → compiled config contains BOTH generic rules AND NAKALA column constraints
  - POST /api/jobs with template_id=generic_default without overlay
    → purely generic config (no nakala:* column constraints)
  - NAKALA columns have required=True and correct constraints (regex, allowed_values)
  - Generic hygiene rules apply to NAKALA columns
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


def _upload(columns: list[str], rows: list[list[str]], template_id: str = "generic_default",
            overlay_id: str = "") -> str:
    csv_bytes = _make_csv(columns, rows)
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1", "template_id": template_id, "overlay_id": overlay_id},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["job_id"]


def _get_column_config(job_id: str) -> dict:
    resp = client.get(f"/api/jobs/{job_id}/column-config")
    assert resp.status_code == 200
    data = resp.json()
    # Endpoint wraps columns under {"columns": {...}}
    return data.get("columns", data)


def _validate(job_id: str) -> dict:
    resp = client.post(f"/api/jobs/{job_id}/validate")
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Test 1 — overlay=nakala_extended contient les règles génériques ET NAKALA
# ---------------------------------------------------------------------------

def test_overlay_nakala_extended_has_generic_and_nakala_rules():
    """With generic_default + nakala_extended overlay, column-config must include
    NAKALA columns (required, constrained) AND generic wildcard settings."""
    columns = [
        "nakala:type", "nakala:title", "nakala:creator",
        "nakala:created", "nakala:license",
    ]
    rows = [["http://purl.org/coar/resource_type/c_c513", "Mon titre", "Dupont, Jean",
             "2024", "CC-BY-4.0"]]

    job_id = _upload(columns, rows, template_id="generic_default", overlay_id="nakala_extended")
    cfg = _get_column_config(job_id)

    # NAKALA columns must be present with constraints
    assert "nakala:type" in cfg, "nakala:type should be in column config"
    assert cfg["nakala:type"].get("required") is True, "nakala:type must be required"

    assert "nakala:created" in cfg
    assert cfg["nakala:created"].get("required") is True

    assert "nakala:creator" in cfg
    # The regex for creator should be present (from overlay)
    assert cfg["nakala:creator"].get("regex") is not None


def test_overlay_nakala_generic_rules_apply():
    """Validate with overlay: hygiene issues should be detected on NAKALA columns."""
    columns = ["nakala:type", "nakala:title", "nakala:creator", "nakala:created", "nakala:license"]
    rows = [
        # nakala:title has leading space → hygiene warning
        ["http://purl.org/coar/resource_type/c_c513", "  Titre avec espace", "Dupont, Jean",
         "2024", "CC-BY-4.0"],
    ]

    job_id = _upload(columns, rows, template_id="generic_default", overlay_id="nakala_extended")
    result = _validate(job_id)

    # At least hygiene issues should be detected (leading space in title)
    total = result.get("résumé", {}).get("total", 0)
    assert total > 0, "Should detect at least one issue (hygiene on nakala:title)"


# ---------------------------------------------------------------------------
# Test 2 — sans overlay : config générique normale, pas de colonnes NAKALA
# ---------------------------------------------------------------------------

def test_no_overlay_generic_config():
    """With generic_default and no overlay, nakala:type is NOT marked required."""
    columns = ["nakala:type", "nakala:title", "auteur"]
    rows = [["texte_quelconque", "Titre", "Auteur"]]

    job_id = _upload(columns, rows, template_id="generic_default", overlay_id="")
    cfg = _get_column_config(job_id)

    # Without overlay, nakala:type should not be specially constrained
    nakala_type_cfg = cfg.get("nakala:type", {})
    assert not nakala_type_cfg.get("required", False), (
        "Without overlay, nakala:type should NOT be required by the generic template"
    )
    # No allowed_values constraint from overlay
    assert not nakala_type_cfg.get("allowed_values"), (
        "Without overlay, nakala:type should not have controlled vocabulary"
    )


# ---------------------------------------------------------------------------
# Test 3 — overlay=nakala_baseline : colonnes requises avec contraintes
# ---------------------------------------------------------------------------

def test_overlay_nakala_baseline_required_columns():
    """nakala_baseline overlay marks 5 mandatory NAKALA columns as required."""
    columns = ["nakala:type", "nakala:title", "nakala:creator", "nakala:created", "nakala:license"]
    rows = [["http://purl.org/coar/resource_type/c_c513", "Titre", "Nom, Prénom", "2024",
             "CC-BY-4.0"]]

    job_id = _upload(columns, rows, template_id="generic_default", overlay_id="nakala_baseline")
    cfg = _get_column_config(job_id)

    required_cols = ["nakala:type", "nakala:title", "nakala:creator", "nakala:created",
                     "nakala:license"]
    for col in required_cols:
        assert col in cfg, f"{col} should be in column config"
        assert cfg[col].get("required") is True, f"{col} should be required"


# ---------------------------------------------------------------------------
# Test 4 — les allowed_values NAKALA sont bien lockées dans l'overlay
# ---------------------------------------------------------------------------

def test_overlay_nakala_type_has_locked_allowed_values():
    """nakala:type should have allowed_values (COAR list) locked from the overlay."""
    columns = ["nakala:type", "nakala:title", "nakala:creator", "nakala:created", "nakala:license"]
    rows = [["http://purl.org/coar/resource_type/c_c513", "T", "Nom, P", "2024", "CC-BY-4.0"]]

    job_id = _upload(columns, rows, template_id="generic_default", overlay_id="nakala_baseline")
    cfg = _get_column_config(job_id)

    nakala_type = cfg.get("nakala:type", {})
    assert len(nakala_type.get("allowed_values", [])) > 0, (
        "nakala:type should have allowed_values from the overlay"
    )
    assert nakala_type.get("allowed_values_locked") is True, (
        "nakala:type allowed_values should be locked"
    )
