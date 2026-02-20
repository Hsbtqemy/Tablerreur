"""Tests for exporters."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pandas as pd
import pytest

from spreadsheet_qa.core.exporters import CSVExporter, IssuesCSVExporter, TXTReporter, XLSXExporter
from spreadsheet_qa.core.models import Issue, IssueStatus, Severity


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "Titre": ["Introduction ; à la vie", '"Quoted"', "Normal"],
            "Auteur": ["Jean Dupont", "Marie Martin", "Pierre"],
            "Date": ["2021", "2020", "2019"],
        }
    )


@pytest.fixture
def sample_issues():
    return [
        Issue.create(
            rule_id="generic.hygiene.leading_trailing_space",
            severity=Severity.WARNING,
            row=0,
            col="Titre",
            original="Introduction ; à la vie ",
            message="Trailing space",
            suggestion="Introduction ; à la vie",
        )
    ]


class TestCSVExporter:
    def test_delimiter_is_semicolon(self, sample_df, tmp_path):
        path = tmp_path / "out.csv"
        CSVExporter().export(sample_df, path)
        content = path.read_text(encoding="utf-8")
        # Parse with semicolon — should produce correct columns
        reader = csv.reader(io.StringIO(content), delimiter=";")
        rows = list(reader)
        assert rows[0] == ["Titre", "Auteur", "Date"]

    def test_values_with_semicolon_are_quoted(self, sample_df, tmp_path):
        path = tmp_path / "out.csv"
        CSVExporter().export(sample_df, path)
        content = path.read_text(encoding="utf-8")
        # "Introduction ; à la vie" contains ; → must be quoted
        assert '"Introduction ; à la vie"' in content

    def test_utf8_no_bom_by_default(self, sample_df, tmp_path):
        path = tmp_path / "out.csv"
        CSVExporter().export(sample_df, path, bom=False)
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")  # no BOM

    def test_utf8_bom_when_requested(self, sample_df, tmp_path):
        path = tmp_path / "out.csv"
        CSVExporter().export(sample_df, path, bom=True)
        raw = path.read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf")

    def test_roundtrip(self, sample_df, tmp_path):
        path = tmp_path / "out.csv"
        CSVExporter().export(sample_df, path)
        df2 = pd.read_csv(path, sep=";", dtype=str)
        assert list(df2.columns) == list(sample_df.columns)
        assert len(df2) == len(sample_df)


class TestXLSXExporter:
    def test_creates_xlsx_file(self, sample_df, tmp_path):
        path = tmp_path / "out.xlsx"
        XLSXExporter().export(sample_df, path)
        assert path.exists()

    def test_xlsx_has_correct_data(self, sample_df, tmp_path):
        path = tmp_path / "out.xlsx"
        XLSXExporter().export(sample_df, path)
        df2 = pd.read_excel(path, dtype=str, engine="openpyxl")
        assert list(df2.columns) == list(sample_df.columns)
        assert len(df2) == len(sample_df)


class TestIssuesCSVExporter:
    def test_delimiter_is_semicolon(self, sample_issues, tmp_path):
        path = tmp_path / "issues.csv"
        IssuesCSVExporter().export(sample_issues, path)
        content = path.read_text(encoding="utf-8")
        reader = csv.reader(io.StringIO(content), delimiter=";")
        rows = list(reader)
        # First row = French headers
        assert "identifiant" in rows[0]
        assert "sévérité" in rows[0]
        assert "colonne" in rows[0]

    def test_row_is_1_based(self, sample_issues, tmp_path):
        path = tmp_path / "issues.csv"
        IssuesCSVExporter().export(sample_issues, path)
        content = path.read_text(encoding="utf-8")
        reader = csv.DictReader(io.StringIO(content), delimiter=";")
        rows = list(reader)
        assert rows[0]["ligne"] == "1"  # French header; 0 → 1 in export


class TestTXTReporter:
    def test_creates_report_file(self, sample_issues, tmp_path):
        path = tmp_path / "report.txt"
        TXTReporter().export(sample_issues, path)
        assert path.exists()

    def test_report_contains_severity(self, sample_issues, tmp_path):
        path = tmp_path / "report.txt"
        TXTReporter().export(sample_issues, path)
        content = path.read_text(encoding="utf-8")
        # Report uses French severity labels
        assert "Avertissement" in content

    def test_report_contains_column_name(self, sample_issues, tmp_path):
        path = tmp_path / "report.txt"
        TXTReporter().export(sample_issues, path)
        content = path.read_text(encoding="utf-8")
        assert "Titre" in content
