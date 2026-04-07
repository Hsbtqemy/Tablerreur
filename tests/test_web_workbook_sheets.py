"""Sélection de feuille à l'import (XLSX multi-feuilles)."""

from __future__ import annotations

import io

import pandas as pd
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from spreadsheet_qa.core.dataset import list_workbook_sheet_names_from_bytes  # noqa: E402
from spreadsheet_qa.web.app import app  # noqa: E402

client = TestClient(app)


def _make_xlsx_two_sheets() -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame({"col_a": ["1"]}).to_excel(writer, sheet_name="Feuil_A", index=False)
        pd.DataFrame({"col_b": ["2"]}).to_excel(writer, sheet_name="Feuil_B", index=False)
    return buf.getvalue()


def test_list_workbook_sheet_names_from_bytes_xlsx() -> None:
    raw = _make_xlsx_two_sheets()
    names = list_workbook_sheet_names_from_bytes(raw, "test.xlsx")
    assert names == ["Feuil_A", "Feuil_B"]


def test_inspect_workbook_sheets_ok() -> None:
    raw = _make_xlsx_two_sheets()
    resp = client.post(
        "/api/inspect-workbook-sheets",
        files={
            "file": (
                "classeur.xlsx",
                io.BytesIO(raw),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert resp.status_code == 200
    assert resp.json()["sheets"] == ["Feuil_A", "Feuil_B"]


def test_inspect_workbook_sheets_rejects_csv() -> None:
    resp = client.post(
        "/api/inspect-workbook-sheets",
        files={"file": ("a.csv", io.BytesIO(b"a;b\n1;2"), "text/csv")},
    )
    assert resp.status_code == 415


def test_create_job_with_sheet_name() -> None:
    raw = _make_xlsx_two_sheets()
    resp = client.post(
        "/api/jobs",
        files={
            "file": (
                "classeur.xlsx",
                io.BytesIO(raw),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={"header_row": "1", "sheet_name": "Feuil_B"},
    )
    assert resp.status_code == 200
    assert resp.json()["columns"] == ["col_b"]
