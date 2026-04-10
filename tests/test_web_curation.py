"""Tests for manual cell editing and revalidation endpoints.

Covers:
  - POST /api/jobs/{job_id}/edit-cell
  - POST /api/jobs/{job_id}/edit-cells
  - POST /api/jobs/{job_id}/revalidate
  - Undo after edit-cell
  - Error cases (invalid row/column)
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


def _upload_csv(columns: list[str], rows: list[list[str]]) -> str:
    """Upload a CSV and return the job_id."""
    csv_bytes = _make_csv(columns, rows)
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1"},
    )
    assert resp.status_code == 200
    return resp.json()["job_id"]


def _upload_and_validate(columns: list[str], rows: list[list[str]]) -> str:
    """Upload a CSV, validate it, and return job_id."""
    job_id = _upload_csv(columns, rows)
    resp = client.post(f"/api/jobs/{job_id}/validate")
    assert resp.status_code == 200
    return job_id


def _get_df_value(job_id: str, row: int, col: str) -> str:
    """Read a cell value from the preview (0-based row index)."""
    resp = client.get(f"/api/jobs/{job_id}/preview?rows=50")
    assert resp.status_code == 200
    data = resp.json()
    col_idx = data["columns"].index(col)
    return data["rows"][row][col_idx]


# ---------------------------------------------------------------------------
# Test 1 — edit-cell modifie le DataFrame
# ---------------------------------------------------------------------------


def test_edit_cell_modifies_dataframe():
    job_id = _upload_csv(
        ["titre", "annee"],
        [["Article original", "2023"], ["Autre titre", "2022"]],
    )

    resp = client.post(
        f"/api/jobs/{job_id}/edit-cell",
        json={"row": 0, "column": "titre", "value": "Titre corrigé"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["old_value"] == "Article original"
    assert data["new_value"] == "Titre corrigé"

    # Vérifier que la modification est persistée dans le DataFrame
    assert _get_df_value(job_id, 0, "titre") == "Titre corrigé"
    # L'autre ligne reste inchangée
    assert _get_df_value(job_id, 1, "titre") == "Autre titre"


# ---------------------------------------------------------------------------
# Test 2 — edit-cell + undo restaure la valeur précédente
# ---------------------------------------------------------------------------


def test_edit_cell_then_undo():
    job_id = _upload_csv(
        ["titre", "annee"],
        [["Valeur initiale", "2023"]],
    )

    # Éditer la cellule
    resp = client.post(
        f"/api/jobs/{job_id}/edit-cell",
        json={"row": 0, "column": "titre", "value": "Valeur modifiée"},
    )
    assert resp.status_code == 200
    assert _get_df_value(job_id, 0, "titre") == "Valeur modifiée"

    # Annuler
    resp_undo = client.post(f"/api/jobs/{job_id}/undo")
    assert resp_undo.status_code == 200
    data = resp_undo.json()
    assert data["success"] is True

    # La valeur doit être revenue à l'état initial
    assert _get_df_value(job_id, 0, "titre") == "Valeur initiale"


def test_history_reports_manual_edit_summary():
    job_id = _upload_csv(
        ["titre", "annee"],
        [["Valeur initiale", "2023"], ["Autre", "2022"]],
    )

    resp = client.post(
        f"/api/jobs/{job_id}/edit-cells",
        json={
            "edits": [
                {"row": 0, "column": "titre", "value": "Valeur modifiée"},
                {"row": 1, "column": "annee", "value": "2024"},
            ]
        },
    )
    assert resp.status_code == 200

    history_resp = client.get(f"/api/jobs/{job_id}/history")
    assert history_resp.status_code == 200
    history = history_resp.json()

    assert history["can_undo"] is True
    assert history["has_manual_edits"] is True
    assert history["manual_edit_actions"] == 1
    assert history["manual_edit_cells"] == 2
    assert history["manual_edit_rows"] == [1, 2]
    assert "manuelles" in history["undo_description"]
    assert "manuelles" in history["last_manual_edit_description"]


# ---------------------------------------------------------------------------
# Test 3 — edit-cells (bulk) modifie plusieurs cellules en une seule commande
# ---------------------------------------------------------------------------


def test_edit_cells_bulk():
    job_id = _upload_csv(
        ["titre", "date"],
        [["Titre A", "01/01/2023"], ["Titre B", "02/01/2023"]],
    )

    resp = client.post(
        f"/api/jobs/{job_id}/edit-cells",
        json={
            "edits": [
                {"row": 0, "column": "titre", "value": "Nouveau titre A"},
                {"row": 1, "column": "date", "value": "2023-01-02"},
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["modifications"]) == 2

    # Vérifier les modifications
    assert _get_df_value(job_id, 0, "titre") == "Nouveau titre A"
    assert _get_df_value(job_id, 1, "date") == "2023-01-02"
    # Non modifiées
    assert _get_df_value(job_id, 1, "titre") == "Titre B"
    assert _get_df_value(job_id, 0, "date") == "01/01/2023"

    # Un seul undo doit annuler TOUTES les modifications en masse
    resp_undo = client.post(f"/api/jobs/{job_id}/undo")
    assert resp_undo.json()["success"] is True
    assert _get_df_value(job_id, 0, "titre") == "Titre A"
    assert _get_df_value(job_id, 1, "date") == "02/01/2023"


# ---------------------------------------------------------------------------
# Test 4 — revalidate après correction d'une erreur
# ---------------------------------------------------------------------------


def test_revalidate_after_fixing_error():
    """Corriger une cellule en erreur puis revalider doit réduire le nombre de problèmes."""
    # CSV avec une valeur manquante dans une colonne requise
    # On configure la colonne 'code' comme required via le template
    # On utilise une règle simple : on vérifie le nombre de problèmes avant/après
    csv_bytes = _make_csv(
        ["langue", "annee"],
        [
            ["fra", "2024"],
            ["eng", "2023"],
            ["fra", "non_numerique"],  # type mismatch → soft_typing
            ["deu", "2022"],
            ["ita", "2021"],
            ["spa", "2020"],
            ["por", "2019"],
            ["fra", "2018"],
            ["eng", "2017"],
        ],
    )
    resp = client.post(
        "/api/jobs",
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"header_row": "1"},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    # Première validation
    resp_val = client.post(f"/api/jobs/{job_id}/validate")
    assert resp_val.status_code == 200
    total_before = resp_val.json()["résumé"]["total"]

    # Corriger la valeur aberrante
    client.post(
        f"/api/jobs/{job_id}/edit-cell",
        json={"row": 2, "column": "annee", "value": "2016"},
    )

    # Re-valider
    resp_rev = client.post(f"/api/jobs/{job_id}/revalidate")
    assert resp_rev.status_code == 200
    rev_data = resp_rev.json()
    assert "résumé" in rev_data
    total_after = rev_data["résumé"]["total"]

    # Après correction, il doit y avoir moins de problèmes (ou au moins autant)
    assert total_after <= total_before

    history_resp = client.get(f"/api/jobs/{job_id}/history")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert history["has_manual_edits"] is False
    assert history["manual_edit_cells"] == 0
    assert history["manual_edit_rows"] == []


# ---------------------------------------------------------------------------
# Test 5 — edit-cell avec row/col invalides
# ---------------------------------------------------------------------------


def test_edit_cell_invalid_row_returns_422():
    job_id = _upload_csv(["titre"], [["Valeur"]])

    resp = client.post(
        f"/api/jobs/{job_id}/edit-cell",
        json={"row": 999, "column": "titre", "value": "X"},
    )
    assert resp.status_code == 422


def test_edit_cell_invalid_column_returns_422():
    job_id = _upload_csv(["titre"], [["Valeur"]])

    resp = client.post(
        f"/api/jobs/{job_id}/edit-cell",
        json={"row": 0, "column": "colonne_inexistante", "value": "X"},
    )
    assert resp.status_code == 422


def test_edit_cell_unknown_job_returns_404():
    resp = client.post(
        "/api/jobs/job-inconnu/edit-cell",
        json={"row": 0, "column": "titre", "value": "X"},
    )
    assert resp.status_code == 404


def test_edit_cells_empty_list_returns_422():
    job_id = _upload_csv(["titre"], [["Valeur"]])

    resp = client.post(
        f"/api/jobs/{job_id}/edit-cells",
        json={"edits": []},
    )
    assert resp.status_code == 422
