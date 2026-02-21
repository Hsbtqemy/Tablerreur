"""Tests for NakalaClient and nakala.* validation rules."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from spreadsheet_qa.core.nakala_api import NakalaClient
from spreadsheet_qa.core.rules.nakala_rules import (
    NakalaCreatedFormatRule,
    NakalaDepositTypeRule,
    NakalaLanguageRule,
    NakalaLicenseRule,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COAR_URIS = [
    "http://purl.org/coar/resource_type/c_ddb1",
    "http://purl.org/coar/resource_type/c_5ce6",
    "http://purl.org/coar/resource_type/c_2f33",
]

SPDX_LICENSES_RAW = [
    {"code": "CC-BY-4.0", "name": "Creative Commons Attribution 4.0"},
    {"code": "CC0-1.0", "name": "Creative Commons Zero v1.0 Universal"},
    {"code": "MIT", "name": "MIT License"},
]

LANGUAGES_RAW = [
    {"id": "fra", "label": "French"},
    {"id": "eng", "label": "English"},
    {"id": "deu", "label": "German"},
]


def _mock_client_cls(return_value):
    """Return a mock httpx.Client context manager that yields a mock with get() returning return_value."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = return_value
    mock_resp.raise_for_status.return_value = None
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_cls = MagicMock()
    mock_cls.return_value.__enter__.return_value = mock_ctx
    mock_cls.return_value.__exit__.return_value = False
    return mock_cls


def _patched_client(tmp_cache: Path, endpoint_data: dict) -> NakalaClient:
    """NakalaClient whose _fetch_sync returns pre-defined data per endpoint."""
    client = NakalaClient(cache_path=tmp_cache)
    client._fetch_sync = lambda ep: endpoint_data.get(ep, [])
    return client


# ---------------------------------------------------------------------------
# Audit 1 — fetch_deposit_types
# ---------------------------------------------------------------------------


class TestFetchDepositTypes:
    def test_parses_flat_string_list(self, tmp_path):
        client = NakalaClient(cache_path=tmp_path / "cache.json")
        client._fetch_sync = lambda ep: COAR_URIS
        result = client.fetch_deposit_types()
        assert result == COAR_URIS

    def test_ignores_dict_items(self, tmp_path):
        """Old/wrong API format (dicts) must be filtered out."""
        client = NakalaClient(cache_path=tmp_path / "cache.json")
        client._fetch_sync = lambda ep: [{"id": "not_a_uri"}, COAR_URIS[0]]
        result = client.fetch_deposit_types()
        assert result == [COAR_URIS[0]]

    def test_uses_datatypes_endpoint(self, tmp_path):
        called = []
        client = NakalaClient(cache_path=tmp_path / "cache.json")
        client._fetch_sync = lambda ep: called.append(ep) or []
        client.fetch_deposit_types()
        assert any("datatypes" in ep for ep in called)

    def test_returns_empty_on_network_error(self, tmp_path):
        client = NakalaClient(cache_path=tmp_path / "cache.json")
        with patch("spreadsheet_qa.core.nakala_api._HTTPX_AVAILABLE", True):
            with patch("spreadsheet_qa.core.nakala_api.httpx") as mock_httpx:
                mock_httpx.Client.return_value.__enter__.return_value.get.side_effect = (
                    OSError("network error")
                )
                result = client.fetch_deposit_types()
        assert result == []


# ---------------------------------------------------------------------------
# Audit 2 — fetch_licenses
# ---------------------------------------------------------------------------


class TestFetchLicenses:
    def test_extracts_code_field(self, tmp_path):
        client = NakalaClient(cache_path=tmp_path / "cache.json")
        client._fetch_sync = lambda ep: SPDX_LICENSES_RAW
        result = client.fetch_licenses()
        assert result == ["CC-BY-4.0", "CC0-1.0", "MIT"]

    def test_ignores_items_without_code(self, tmp_path):
        client = NakalaClient(cache_path=tmp_path / "cache.json")
        client._fetch_sync = lambda ep: [
            {"name": "No code here"},
            {"code": "Apache-2.0", "name": "Apache"},
        ]
        result = client.fetch_licenses()
        assert result == ["Apache-2.0"]

    def test_returns_empty_list_for_empty_response(self, tmp_path):
        client = NakalaClient(cache_path=tmp_path / "cache.json")
        client._fetch_sync = lambda ep: []
        result = client.fetch_licenses()
        assert result == []


# ---------------------------------------------------------------------------
# Audit 3 — fetch_languages
# ---------------------------------------------------------------------------


class TestFetchLanguages:
    def test_extracts_id_field(self, tmp_path):
        client = NakalaClient(cache_path=tmp_path / "cache.json")
        client._fetch_sync = lambda ep: LANGUAGES_RAW
        result = client.fetch_languages()
        assert result == ["fra", "eng", "deu"]

    def test_ignores_items_without_id(self, tmp_path):
        client = NakalaClient(cache_path=tmp_path / "cache.json")
        client._fetch_sync = lambda ep: [
            {"label": "no id"},
            {"id": "ita", "label": "Italian"},
        ]
        result = client.fetch_languages()
        assert result == ["ita"]


# ---------------------------------------------------------------------------
# Audit 4 — cache
# ---------------------------------------------------------------------------


class TestCache:
    def test_cache_written_after_http_fetch(self, tmp_path):
        cache_path = tmp_path / "cache.json"
        client = NakalaClient(cache_path=cache_path)

        with patch("spreadsheet_qa.core.nakala_api._HTTPX_AVAILABLE", True):
            mock_cls = _mock_client_cls(COAR_URIS)
            with patch("spreadsheet_qa.core.nakala_api.httpx") as mock_httpx:
                mock_httpx.Client = mock_cls
                client.fetch_deposit_types()

        assert cache_path.exists()
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        assert "/vocabularies/datatypes" in data
        assert data["/vocabularies/datatypes"] == COAR_URIS

    def test_cache_used_on_second_call(self, tmp_path):
        cache_path = tmp_path / "cache.json"
        client = NakalaClient(cache_path=cache_path)

        # Pre-seed cache
        with client._lock:
            client._cache["/vocabularies/datatypes"] = COAR_URIS
            client._save_cache()

        # Second client reads from disk cache, no HTTP needed
        client2 = NakalaClient(cache_path=cache_path)
        result = client2.fetch_deposit_types()
        assert result == COAR_URIS

    def test_corrupt_cache_ignored(self, tmp_path):
        cache_path = tmp_path / "cache.json"
        cache_path.write_text("not valid json", encoding="utf-8")
        client = NakalaClient(cache_path=cache_path)
        assert client._cache == {}


# ---------------------------------------------------------------------------
# Audit 5 — fail-open behaviour
# ---------------------------------------------------------------------------


class TestFailOpen:
    def test_is_valid_deposit_type_true_when_no_vocab(self, tmp_path):
        client = NakalaClient(cache_path=tmp_path / "cache.json")
        client._fetch_sync = lambda ep: []
        # Empty vocab → fail-open → True for any value
        assert client.is_valid_deposit_type("anything") is True

    def test_is_valid_license_true_when_no_vocab(self, tmp_path):
        client = NakalaClient(cache_path=tmp_path / "cache.json")
        client._fetch_sync = lambda ep: []
        assert client.is_valid_license("anything") is True

    def test_is_valid_language_true_when_no_vocab(self, tmp_path):
        client = NakalaClient(cache_path=tmp_path / "cache.json")
        client._fetch_sync = lambda ep: []
        assert client.is_valid_language("anything") is True

    def test_is_valid_deposit_type_false_for_unknown(self, tmp_path):
        client = NakalaClient(cache_path=tmp_path / "cache.json")
        client._fetch_sync = lambda ep: COAR_URIS
        assert client.is_valid_deposit_type("http://purl.org/coar/resource_type/c_ddb1") is True
        assert client.is_valid_deposit_type("not_a_valid_uri") is False


# ---------------------------------------------------------------------------
# Nakala rules — NakalaCreatedFormatRule (offline, no client needed)
# ---------------------------------------------------------------------------


class TestNakalaCreatedFormatRule:
    rule = NakalaCreatedFormatRule()

    def test_valid_yyyy(self):
        df = pd.DataFrame({"nakala:created": ["2024"]})
        assert self.rule.check(df, "nakala:created", {}) == []

    def test_valid_yyyy_mm(self):
        df = pd.DataFrame({"nakala:created": ["2024-01"]})
        assert self.rule.check(df, "nakala:created", {}) == []

    def test_valid_yyyy_mm_dd(self):
        df = pd.DataFrame({"nakala:created": ["2024-01-15"]})
        assert self.rule.check(df, "nakala:created", {}) == []

    def test_invalid_slash_format(self):
        df = pd.DataFrame({"nakala:created": ["15/01/2024"]})
        issues = self.rule.check(df, "nakala:created", {})
        assert len(issues) == 1

    def test_invalid_two_digit_year(self):
        df = pd.DataFrame({"nakala:created": ["24"]})
        issues = self.rule.check(df, "nakala:created", {})
        assert len(issues) == 1

    def test_nan_skipped(self):
        df = pd.DataFrame({"nakala:created": [float("nan")]})
        assert self.rule.check(df, "nakala:created", {}) == []

    def test_empty_string_skipped(self):
        df = pd.DataFrame({"nakala:created": [""]})
        assert self.rule.check(df, "nakala:created", {}) == []

    def test_column_not_present_returns_empty(self):
        df = pd.DataFrame({"other": ["2024"]})
        assert self.rule.check(df, "nakala:created", {}) == []


# ---------------------------------------------------------------------------
# Nakala rules — NakalaDepositTypeRule (requires client)
# ---------------------------------------------------------------------------


class _MockNakalaClient:
    def __init__(self, deposit_types=None, licenses=None, languages=None):
        self._deposit_types = deposit_types or []
        self._licenses = licenses or []
        self._languages = languages or []

    def fetch_deposit_types(self):
        return self._deposit_types

    def fetch_licenses(self):
        return self._licenses

    def fetch_languages(self):
        return self._languages


class TestNakalaDepositTypeRule:
    rule = NakalaDepositTypeRule()
    valid_uri = "http://purl.org/coar/resource_type/c_ddb1"

    def test_valid_type_no_issue(self):
        client = _MockNakalaClient(deposit_types=[self.valid_uri])
        df = pd.DataFrame({"nakala:type": [self.valid_uri]})
        issues = self.rule.check(df, "nakala:type", {"_nakala_client": client})
        assert issues == []

    def test_invalid_type_one_issue(self):
        client = _MockNakalaClient(deposit_types=[self.valid_uri])
        df = pd.DataFrame({"nakala:type": ["not_a_coar_uri"]})
        issues = self.rule.check(df, "nakala:type", {"_nakala_client": client})
        assert len(issues) == 1
        assert "not_a_coar_uri" in issues[0].message

    def test_no_client_skips_silently(self):
        df = pd.DataFrame({"nakala:type": ["anything"]})
        issues = self.rule.check(df, "nakala:type", {})
        assert issues == []

    def test_empty_vocab_skips_silently(self):
        client = _MockNakalaClient(deposit_types=[])
        df = pd.DataFrame({"nakala:type": ["anything"]})
        issues = self.rule.check(df, "nakala:type", {"_nakala_client": client})
        assert issues == []

    def test_nan_skipped(self):
        client = _MockNakalaClient(deposit_types=[self.valid_uri])
        df = pd.DataFrame({"nakala:type": [float("nan")]})
        issues = self.rule.check(df, "nakala:type", {"_nakala_client": client})
        assert issues == []


# ---------------------------------------------------------------------------
# Nakala rules — NakalaLicenseRule
# ---------------------------------------------------------------------------


class TestNakalaLicenseRule:
    rule = NakalaLicenseRule()

    def test_valid_license_no_issue(self):
        client = _MockNakalaClient(licenses=["CC-BY-4.0", "MIT"])
        df = pd.DataFrame({"nakala:license": ["CC-BY-4.0"]})
        issues = self.rule.check(df, "nakala:license", {"_nakala_client": client})
        assert issues == []

    def test_invalid_license_one_issue(self):
        client = _MockNakalaClient(licenses=["CC-BY-4.0"])
        df = pd.DataFrame({"nakala:license": ["INVALID-LICENSE"]})
        issues = self.rule.check(df, "nakala:license", {"_nakala_client": client})
        assert len(issues) == 1

    def test_no_client_skips(self):
        df = pd.DataFrame({"nakala:license": ["anything"]})
        assert self.rule.check(df, "nakala:license", {}) == []


# ---------------------------------------------------------------------------
# Nakala rules — NakalaLanguageRule
# ---------------------------------------------------------------------------


class TestNakalaLanguageRule:
    rule = NakalaLanguageRule()

    def test_valid_iso639_3_no_issue(self):
        client = _MockNakalaClient(languages=["fra", "eng", "deu"])
        df = pd.DataFrame({"dcterms:language": ["fra"]})
        issues = self.rule.check(df, "dcterms:language", {"_nakala_client": client})
        assert issues == []

    def test_invalid_language_one_issue(self):
        client = _MockNakalaClient(languages=["fra", "eng"])
        df = pd.DataFrame({"dcterms:language": ["zz"]})
        issues = self.rule.check(df, "dcterms:language", {"_nakala_client": client})
        assert len(issues) == 1

    def test_no_client_skips(self):
        df = pd.DataFrame({"dcterms:language": ["xx"]})
        assert self.rule.check(df, "dcterms:language", {}) == []

    def test_default_severity_is_warning(self):
        client = _MockNakalaClient(languages=["fra"])
        df = pd.DataFrame({"dcterms:language": ["zz"]})
        issues = self.rule.check(df, "dcterms:language", {"_nakala_client": client})
        assert len(issues) == 1
        from spreadsheet_qa.core.models import Severity
        assert issues[0].severity == Severity.WARNING
