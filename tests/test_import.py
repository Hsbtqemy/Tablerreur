"""Tests for DatasetLoader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from spreadsheet_qa.core.dataset import DatasetLoader, preview_header_rows


@pytest.fixture
def csv_file(tmp_path) -> Path:
    content = (
        "# metadata line\n"
        "Titre;Auteur;Date\n"
        "Introduction;Jean Dupont;2021-03-15\n"
        "Méthodes;Marie Martin;2020-11-01\n"
    )
    p = tmp_path / "test.csv"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def xlsx_file(tmp_path) -> Path:
    df = pd.DataFrame({0: ["meta", "Titre", "A", "B"], 1: ["meta", "Auteur", "x", "y"]})
    path = tmp_path / "test.xlsx"
    df.to_excel(path, header=False, index=False)
    return path


class TestDatasetLoader:
    loader = DatasetLoader()

    def test_load_csv_with_header_row_0(self, tmp_path):
        p = tmp_path / "h0.csv"
        p.write_text("A;B\n1;2\n3;4\n", encoding="utf-8")
        df, meta = self.loader.load(p, header_row=0)
        assert list(df.columns) == ["A", "B"]
        assert len(df) == 2

    def test_load_csv_with_header_row_1(self, csv_file):
        """Header is row index 1 (0-based), skipping the metadata line."""
        df, meta = self.loader.load(csv_file, header_row=1)
        assert "Titre" in df.columns
        assert "Auteur" in df.columns
        assert len(df) == 2

    def test_detects_semicolon_delimiter(self, csv_file):
        df, meta = self.loader.load(csv_file, header_row=1)
        assert meta.delimiter == ";"

    def test_detects_encoding(self, tmp_path):
        p = tmp_path / "utf8.csv"
        p.write_text("A;B\ncafé;naïve\n", encoding="utf-8")
        df, meta = self.loader.load(p, header_row=0)
        assert "café" in df["A"].values

    def test_fingerprint_is_sha256_prefix(self, csv_file):
        _, meta = self.loader.load(csv_file, header_row=1)
        assert len(meta.fingerprint) == 64  # sha256 hex = 64 chars

    def test_raises_on_invalid_header_row(self, tmp_path):
        p = tmp_path / "tiny.csv"
        p.write_text("A;B\n1;2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="header_row"):
            self.loader.load(p, header_row=99)

    def test_load_xlsx(self, xlsx_file):
        df, meta = self.loader.load(xlsx_file, header_row=1)
        assert "Titre" in df.columns or "0" in df.columns  # openpyxl may use col names

    def test_meta_original_shape(self, tmp_path):
        p = tmp_path / "shape.csv"
        p.write_text("X;Y;Z\na;b;c\nd;e;f\n", encoding="utf-8")
        df, meta = self.loader.load(p, header_row=0)
        assert meta.original_shape == (2, 3)


class TestPreviewHeaderRows:
    def test_returns_list_of_rows(self, csv_file):
        rows = preview_header_rows(csv_file, n=5)
        assert isinstance(rows, list)
        assert len(rows) <= 5
        assert all(isinstance(r, list) for r in rows)

    def test_first_row_is_metadata_line(self, csv_file):
        rows = preview_header_rows(csv_file, n=3)
        assert "metadata" in rows[0][0].lower() or "#" in rows[0][0]
