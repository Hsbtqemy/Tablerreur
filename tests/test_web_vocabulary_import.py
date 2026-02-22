"""Tests for POST /api/jobs/{job_id}/import-vocabulary.

Covers:
  - YAML avec structure { values: [...] }
  - YAML avec juste une liste [...]
  - YAML avec { name: str, values: [...] }
  - Fichier .txt (une valeur par ligne)
  - Fichier invalide → 422
  - YAML vide / sans clé values → 422
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


def _upload_csv() -> str:
    """Create a job and return its job_id."""
    csv_bytes = _make_csv(["langue", "titre"], [["fra", "Test"], ["eng", "Hello"]])
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1"},
    )
    assert resp.status_code == 200
    return resp.json()["job_id"]


def _post_vocab(job_id: str, content: bytes, filename: str, content_type: str = "application/x-yaml"):
    return client.post(
        f"/api/jobs/{job_id}/import-vocabulary",
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_import_vocabulary_yaml_with_values_key():
    job_id = _upload_csv()
    yaml_content = b"name: Langues\nvalues:\n  - fra\n  - eng\n  - deu\n"
    resp = _post_vocab(job_id, yaml_content, "langues.yml")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Langues"
    assert data["values"] == ["fra", "eng", "deu"]
    assert data["count"] == 3


def test_import_vocabulary_yaml_bare_list():
    job_id = _upload_csv()
    yaml_content = b"- fra\n- eng\n- spa\n- ita\n"
    resp = _post_vocab(job_id, yaml_content, "langues.yaml")
    assert resp.status_code == 200
    data = resp.json()
    assert data["values"] == ["fra", "eng", "spa", "ita"]
    assert data["count"] == 4


def test_import_vocabulary_yaml_with_name_and_values():
    job_id = _upload_csv()
    yaml_content = b"name: 'Langues acceptees'\nvalues:\n  - fra\n  - eng\n"
    resp = _post_vocab(job_id, yaml_content, "vocab.yml")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Langues acceptees"
    assert set(data["values"]) == {"fra", "eng"}


def test_import_vocabulary_txt_one_per_line():
    job_id = _upload_csv()
    txt_content = b"fra\neng\ndeu\nspa\n"
    resp = _post_vocab(job_id, txt_content, "langues.txt", content_type="text/plain")
    assert resp.status_code == 200
    data = resp.json()
    assert data["values"] == ["fra", "eng", "deu", "spa"]
    assert data["count"] == 4


def test_import_vocabulary_txt_ignores_blank_lines():
    job_id = _upload_csv()
    txt_content = b"fra\n\neng\n  \ndeu\n"
    resp = _post_vocab(job_id, txt_content, "l.txt", content_type="text/plain")
    assert resp.status_code == 200
    assert resp.json()["count"] == 3


def test_import_vocabulary_invalid_yaml_returns_422():
    job_id = _upload_csv()
    invalid = b"key: : bad yaml [\n"
    resp = _post_vocab(job_id, invalid, "bad.yml")
    assert resp.status_code == 422
    assert "valide" in resp.json()["detail"]


def test_import_vocabulary_yaml_dict_without_values_returns_422():
    job_id = _upload_csv()
    yaml_content = b"name: Langues\ndescription: pas de cle values\n"
    resp = _post_vocab(job_id, yaml_content, "no_values.yml")
    assert resp.status_code == 422


def test_import_vocabulary_empty_txt_returns_422():
    job_id = _upload_csv()
    resp = _post_vocab(job_id, b"   \n\n", "empty.txt", content_type="text/plain")
    assert resp.status_code == 422


def test_import_vocabulary_unknown_job_returns_404():
    resp = _post_vocab("nonexistent-id", b"- fra\n", "l.yml")
    assert resp.status_code == 404
