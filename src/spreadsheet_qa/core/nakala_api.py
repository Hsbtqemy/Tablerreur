"""NAKALA API client with disk caching.

Fetches controlled vocabularies from api.nakala.fr:
- Deposit types (COAR resource type URIs)
- Licenses (SPDX codes)
- Languages (ISO 639-3 codes)

All results are cached to disk as nakala_cache.json.
Network calls are made asynchronously in a worker thread.

API response formats (verified 2026-02):
  GET /vocabularies/datatypes  → flat list of COAR URI strings
  GET /vocabularies/licenses   → [{"code": "CC-BY-4.0", "name": "..."}, ...]
  GET /vocabularies/languages  → [{"id": "fra", "label": "..."}, ...]
"""

from __future__ import annotations

import logging

_log = logging.getLogger(__name__)

import json
import threading
from pathlib import Path
from typing import Callable

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False


_BASE_URL = "https://api.nakala.fr"

_ENDPOINTS = {
    "deposit_types": "/vocabularies/datatypes",          # flat list of COAR URI strings
    "licenses": "/vocabularies/licenses",                # [{"code": "CC-BY-4.0", "name": ...}]
    "languages": "/vocabularies/languages?limit=10000",  # [{"id": "fra", "label": ...}]
}


class NakalaClient:
    """Fetch and cache NAKALA controlled vocabularies."""

    def __init__(self, cache_path: Path, timeout: float = 10.0) -> None:
        self._cache_path = cache_path
        self._timeout = timeout
        self._cache: dict = self._load_cache()
        self._lock = threading.Lock()

    def _load_cache(self) -> dict:
        if self._cache_path.exists():
            try:
                return json.loads(self._cache_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_cache(self) -> None:
        try:
            self._cache_path.write_text(
                json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _fetch_sync(self, endpoint: str) -> list:
        """Synchronous fetch with disk caching."""
        with self._lock:
            if endpoint in self._cache:
                return self._cache[endpoint]

        if not _HTTPX_AVAILABLE:
            return []

        try:
            with httpx.Client(timeout=self._timeout) as client:
                r = client.get(f"{_BASE_URL}{endpoint}")
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            _log.warning("Failed to fetch NAKALA vocab %s: %s", endpoint, exc)
            return []

        with self._lock:
            self._cache[endpoint] = data
            self._save_cache()
        return data

    def fetch_deposit_types(self) -> list[str]:
        """Return COAR resource type URIs.

        The API returns a flat list of URI strings, e.g.:
        ["http://purl.org/coar/resource_type/c_ddb1", ...]
        """
        data = self._fetch_sync(_ENDPOINTS["deposit_types"])
        return [item for item in data if isinstance(item, str)]

    def fetch_licenses(self) -> list[str]:
        """Return SPDX license codes.

        The API returns [{"code": "CC-BY-4.0", "name": "..."}, ...].
        """
        data = self._fetch_sync(_ENDPOINTS["licenses"])
        return [item["code"] for item in data if isinstance(item, dict) and "code" in item]

    def fetch_languages(self) -> list[str]:
        """Return ISO 639-3 language codes.

        The API returns [{"id": "fra", "label": "..."}, ...].
        """
        data = self._fetch_sync(_ENDPOINTS["languages"])
        return [item["id"] for item in data if isinstance(item, dict) and "id" in item]

    def fetch_all_async(self, on_done: Callable[[], None] | None = None) -> None:
        """Fetch all vocabularies in a background thread."""
        def _worker():
            self.fetch_deposit_types()
            self.fetch_licenses()
            self.fetch_languages()
            if on_done:
                on_done()

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def is_valid_deposit_type(self, value: str) -> bool:
        types = self.fetch_deposit_types()
        return not types or value in types

    def is_valid_license(self, value: str) -> bool:
        licenses = self.fetch_licenses()
        return not licenses or value in licenses

    def is_valid_language(self, value: str) -> bool:
        languages = self.fetch_languages()
        return not languages or value in languages
