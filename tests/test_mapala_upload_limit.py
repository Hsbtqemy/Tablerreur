"""Limite de taille des uploads Mapala (AUD-P0-02)."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from spreadsheet_qa.web.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_mapala_upload_rejects_second_file_over_limit(client, monkeypatch):
    monkeypatch.setattr("spreadsheet_qa.web.mapala_routes._MAX_UPLOAD_MB", 1)
    monkeypatch.setattr("spreadsheet_qa.web.mapala_routes._MAX_UPLOAD_BYTES", 1024 * 1024)

    small = BytesIO(b"x" * 100)
    big = BytesIO(b"y" * (2 * 1024 * 1024))
    files = {
        "template_file": ("t.xlsx", small, "application/octet-stream"),
        "source_file": ("s.xlsx", big, "application/octet-stream"),
    }
    r = client.post("/api/mapala/upload", files=files)
    assert r.status_code == 413
    assert "Mo" in r.json()["detail"]


def test_mapala_upload_rejects_first_file_over_limit(client, monkeypatch):
    """Le template est lu en premier : 413 avant toute création de job Mapala."""
    monkeypatch.setattr("spreadsheet_qa.web.mapala_routes._MAX_UPLOAD_MB", 1)
    monkeypatch.setattr("spreadsheet_qa.web.mapala_routes._MAX_UPLOAD_BYTES", 1024 * 1024)

    big = BytesIO(b"z" * (2 * 1024 * 1024))
    small = BytesIO(b"a" * 100)
    files = {
        "template_file": ("t.xlsx", big, "application/octet-stream"),
        "source_file": ("s.xlsx", small, "application/octet-stream"),
    }
    r = client.post("/api/mapala/upload", files=files)
    assert r.status_code == 413
    assert "Mo" in r.json()["detail"]


def test_mapala_upload_accepts_two_small_files(client, monkeypatch):
    monkeypatch.setattr("spreadsheet_qa.web.mapala_routes._MAX_UPLOAD_MB", 5)
    monkeypatch.setattr("spreadsheet_qa.web.mapala_routes._MAX_UPLOAD_BYTES", 5 * 1024 * 1024)

    xlsx_stub = BytesIO(
        b"PK\x03\x04"
        + b"\x00" * 200
    )
    files = {
        "template_file": ("t.xlsx", xlsx_stub, "application/octet-stream"),
        "source_file": ("s.xlsx", BytesIO(xlsx_stub.getvalue()), "application/octet-stream"),
    }
    r = client.post("/api/mapala/upload", files=files)
    # Peut être 400 si openpyxl ne lit pas le stub — l’important est de ne pas être 413.
    assert r.status_code != 413
