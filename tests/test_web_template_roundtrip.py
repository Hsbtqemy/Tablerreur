"""Round-trip test: export template → re-import on a new job.

Uses FastAPI's synchronous TestClient (backed by httpx) to exercise the full
HTTP stack without launching a real server.
"""

from __future__ import annotations

import io

import pandas as pd
import pytest
import yaml

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from spreadsheet_qa.web.app import app  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_csv(columns: list[str], rows: list[list[str]]) -> bytes:
    """Build a minimal UTF-8 CSV (semicolon delimiter) as bytes."""
    lines = [";".join(columns)]
    for row in rows:
        lines.append(";".join(row))
    return "\n".join(lines).encode("utf-8")


def _upload_csv(client: TestClient, csv_bytes: bytes, filename: str = "test.csv") -> str:
    """Upload a CSV file and return the job_id."""
    resp = client.post(
        "/api/jobs",
        files={"file": (filename, io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["job_id"]


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


class TestTemplateRoundTrip:
    """Full export → import cycle between two independent jobs."""

    @pytest.fixture(autouse=True)
    def client(self):
        with TestClient(app) as c:
            self.client = c
            yield

    # ------------------------------------------------------------------
    # 1. Create a job and configure several columns
    # ------------------------------------------------------------------

    def _create_configured_job(self) -> str:
        csv = _make_csv(
            ["titre", "date", "langue", "auteur"],
            [
                ["Introduction à la paléographie", "2024-01-15", "fra", "Dupont, Jean"],
                ["Méthodes archivistiques", "2023-06-01", "eng", "Martin, Marie | Leroy, Pierre"],
                ["Corpus médiéval", "2022-11-20", "fra", "Blanc, Sophie"],
            ],
        )
        job_id = _upload_csv(self.client, csv)

        # Configure columns
        config = {
            "columns": {
                "titre": {
                    "required": True,
                    "min_length": 3,
                    "max_length": 200,
                },
                "date": {
                    "required": True,
                    "format_preset": "w3cdtf",
                    "regex": r"^\d{4}(-\d{2}(-\d{2})?)?$",
                },
                "langue": {
                    "required": True,
                    "allowed_values": ["fra", "eng", "deu", "spa", "ita"],
                    "allowed_values_locked": True,
                },
                "auteur": {
                    "list_separator": "|",
                    "list_unique": True,
                },
            }
        }
        resp = self.client.put(
            f"/api/jobs/{job_id}/column-config",
            json=config,
        )
        assert resp.status_code == 200
        return job_id

    # ------------------------------------------------------------------
    # 2. Export template
    # ------------------------------------------------------------------

    def test_export_returns_yaml_attachment(self):
        job_id = self._create_configured_job()
        resp = self.client.get(f"/api/jobs/{job_id}/export-template")
        assert resp.status_code == 200
        assert "application/x-yaml" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        assert ".yml" in resp.headers["content-disposition"]

    def test_export_yaml_is_parseable(self):
        job_id = self._create_configured_job()
        resp = self.client.get(f"/api/jobs/{job_id}/export-template")
        parsed = yaml.safe_load(resp.text)
        assert isinstance(parsed, dict)

    def test_export_contains_configured_columns(self):
        job_id = self._create_configured_job()
        resp = self.client.get(f"/api/jobs/{job_id}/export-template")
        parsed = yaml.safe_load(resp.text)
        cols = parsed.get("columns", {})
        assert "titre" in cols
        assert "date" in cols
        assert "langue" in cols
        assert "auteur" in cols

    def test_export_column_values_match(self):
        job_id = self._create_configured_job()
        resp = self.client.get(f"/api/jobs/{job_id}/export-template")
        parsed = yaml.safe_load(resp.text)
        cols = parsed.get("columns", {})

        assert cols["titre"]["required"] is True
        assert cols["titre"]["min_length"] == 3
        assert cols["titre"]["max_length"] == 200

        assert cols["date"]["required"] is True
        assert cols["date"]["format_preset"] == "w3cdtf"

        assert cols["langue"]["allowed_values"] == ["fra", "eng", "deu", "spa", "ita"]
        assert cols["langue"]["allowed_values_locked"] is True

        assert cols["auteur"]["list_separator"] == "|"
        assert cols["auteur"]["list_unique"] is True

    def test_export_strips_defaults(self):
        """Columns left at default values must NOT appear in the export."""
        csv = _make_csv(["titre", "autre"], [["Test", "valeur"]])
        job_id = _upload_csv(self.client, csv)
        # Configure only "titre", leave "autre" at defaults
        self.client.put(
            f"/api/jobs/{job_id}/column-config",
            json={"columns": {"titre": {"required": True}}},
        )
        resp = self.client.get(f"/api/jobs/{job_id}/export-template")
        parsed = yaml.safe_load(resp.text)
        cols = parsed.get("columns", {})
        # "autre" was never touched — must not appear or be empty
        assert "autre" not in cols or not cols["autre"]

    # ------------------------------------------------------------------
    # 3. Import on a new job
    # ------------------------------------------------------------------

    def test_import_applies_columns(self):
        """Exported YAML can be re-imported and columns are applied."""
        job_id = self._create_configured_job()
        yaml_bytes = self.client.get(f"/api/jobs/{job_id}/export-template").content

        # New job with same columns
        csv = _make_csv(
            ["titre", "date", "langue", "auteur"],
            [["Titre test", "2024-01", "fra", "Auteur, Test"]],
        )
        job2_id = _upload_csv(self.client, csv, "test2.csv")

        resp = self.client.post(
            f"/api/jobs/{job2_id}/import-template",
            files={"file": ("template.yml", io.BytesIO(yaml_bytes), "application/x-yaml")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert set(data["applied"]) >= {"titre", "date", "langue", "auteur"}
        assert data["skipped"] == []

    def test_import_skips_absent_columns(self):
        """Columns in the template that don't exist in the new job are skipped."""
        job_id = self._create_configured_job()
        yaml_bytes = self.client.get(f"/api/jobs/{job_id}/export-template").content

        # New job with only "titre" — "date", "langue", "auteur" are absent
        csv = _make_csv(["titre"], [["Titre seul"]])
        job2_id = _upload_csv(self.client, csv, "partial.csv")

        resp = self.client.post(
            f"/api/jobs/{job2_id}/import-template",
            files={"file": ("template.yml", io.BytesIO(yaml_bytes), "application/x-yaml")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "titre" in data["applied"]
        assert set(data["skipped"]) >= {"date", "langue", "auteur"}

    def test_roundtrip_config_matches(self):
        """After import, the new job's column config matches the original."""
        job_id = self._create_configured_job()
        yaml_bytes = self.client.get(f"/api/jobs/{job_id}/export-template").content

        csv = _make_csv(
            ["titre", "date", "langue", "auteur"],
            [["Titre", "2024-01-01", "fra", "A | B"]],
        )
        job2_id = _upload_csv(self.client, csv, "roundtrip.csv")
        self.client.post(
            f"/api/jobs/{job2_id}/import-template",
            files={"file": ("template.yml", io.BytesIO(yaml_bytes), "application/x-yaml")},
        )

        # Re-export from job2 and compare column configs with the original
        yaml2_bytes = self.client.get(f"/api/jobs/{job2_id}/export-template").content
        cfg1 = yaml.safe_load(yaml_bytes).get("columns", {})
        cfg2 = yaml.safe_load(yaml2_bytes).get("columns", {})

        for col in ("titre", "date", "langue", "auteur"):
            assert cfg2.get(col) == cfg1.get(col), (
                f"Colonne '{col}' diffère après round-trip:\n"
                f"  job1: {cfg1.get(col)}\n  job2: {cfg2.get(col)}"
            )

    # ------------------------------------------------------------------
    # 4. Import validation / error cases
    # ------------------------------------------------------------------

    def test_import_invalid_yaml_returns_422(self):
        csv = _make_csv(["col"], [["v"]])
        job_id = _upload_csv(self.client, csv)
        bad_yaml = b": : invalid: yaml: [\nbroken"
        resp = self.client.post(
            f"/api/jobs/{job_id}/import-template",
            files={"file": ("bad.yml", io.BytesIO(bad_yaml), "application/x-yaml")},
        )
        assert resp.status_code == 422
        assert "valide" in resp.json()["detail"].lower()

    def test_import_yaml_without_structure_returns_422(self):
        csv = _make_csv(["col"], [["v"]])
        job_id = _upload_csv(self.client, csv)
        # Valid YAML but missing 'columns' and 'rules' keys
        bad = yaml.dump({"name": "sans structure"}).encode("utf-8")
        resp = self.client.post(
            f"/api/jobs/{job_id}/import-template",
            files={"file": ("minimal.yml", io.BytesIO(bad), "application/x-yaml")},
        )
        assert resp.status_code == 422

    def test_import_oversized_file_returns_413(self):
        csv = _make_csv(["col"], [["v"]])
        job_id = _upload_csv(self.client, csv)
        big = b"x: y\n" * (1024 * 1024 // 5 + 1)  # > 1 Mo
        resp = self.client.post(
            f"/api/jobs/{job_id}/import-template",
            files={"file": ("big.yml", io.BytesIO(big), "application/x-yaml")},
        )
        assert resp.status_code == 413

    def test_export_empty_config_still_valid(self):
        """Export works even if no columns have been configured (empty config)."""
        csv = _make_csv(["col"], [["v"]])
        job_id = _upload_csv(self.client, csv)
        resp = self.client.get(f"/api/jobs/{job_id}/export-template")
        assert resp.status_code == 200
        parsed = yaml.safe_load(resp.text)
        assert isinstance(parsed, dict)
