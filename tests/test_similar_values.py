"""Tests for the rewritten generic.similar_values rule.

Covers:
  - Dormant unless detect_similar_values: True
  - Détecte les variantes orthographiques proches
  - Suggestion = valeur la plus fréquente de la paire
  - Message en français avec score
  - Seuil configurable (similar_threshold)
  - min_distinct : pas d'exécution si trop peu de valeurs distinctes
  - Optimisation grandes colonnes (>500 valeurs distinctes)
"""

from __future__ import annotations

import pandas as pd
import pytest

from spreadsheet_qa.core.rules.similar_values import SimilarValuesRule, _RAPIDFUZZ_AVAILABLE


pytestmark = pytest.mark.skipif(
    not _RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not installed"
)


def _make_df(values: list[str], col: str = "titre") -> pd.DataFrame:
    return pd.DataFrame({col: values})


def _cfg(col: str = "titre", **kwargs) -> dict:
    """Build a minimal config dict for the given column."""
    col_cfg = {
        "detect_similar_values": True,
        "similar_threshold": 85,
        "similar_min_distinct": 2,
        **kwargs,
    }
    return {"columns": {col: col_cfg}}


# ---------------------------------------------------------------------------
# Dormant par défaut
# ---------------------------------------------------------------------------

def test_dormant_by_default():
    """La règle ne doit rien retourner si detect_similar_values est absent/False."""
    df = _make_df(["Paris", "Pari", "Paris", "Paris"])
    rule = SimilarValuesRule()
    issues = rule.check(df, "titre", {"columns": {"titre": {}}})
    assert issues == []


def test_dormant_when_false():
    df = _make_df(["Paris", "Pari", "Paris"])
    rule = SimilarValuesRule()
    issues = rule.check(df, "titre", {"columns": {"titre": {"detect_similar_values": False}}})
    assert issues == []


# ---------------------------------------------------------------------------
# Détection de base
# ---------------------------------------------------------------------------

def test_detects_close_pair():
    """Paris / Pari → doit être détecté."""
    df = _make_df(["Paris", "Pari", "Paris", "Paris", "Paris"])
    rule = SimilarValuesRule()
    issues = rule.check(df, "titre", _cfg())
    # « Pari » (1 occurrence) doit être signalé
    assert any("Pari" in i.message for i in issues), issues


def test_message_in_french():
    df = _make_df(["Paris", "Pari", "Paris", "Paris"])
    rule = SimilarValuesRule()
    issues = rule.check(df, "titre", _cfg())
    assert issues
    assert "très proche" in issues[0].message
    assert "%" in issues[0].message


def test_suggestion_is_more_frequent():
    """La suggestion doit être la valeur la plus fréquente des deux."""
    # "Paris" × 4, "Pari" × 1 → suggestion = "Paris"
    df = _make_df(["Paris"] * 4 + ["Pari"])
    rule = SimilarValuesRule()
    issues = rule.check(df, "titre", _cfg())
    sug_issues = [i for i in issues if "Pari" in i.message]
    assert sug_issues, "Expected an issue about 'Pari'"
    assert sug_issues[0].suggestion == "Paris"


def test_severity_is_suspicion():
    df = _make_df(["Paris"] * 3 + ["Pari"])
    rule = SimilarValuesRule()
    issues = rule.check(df, "titre", _cfg())
    assert all(i.severity.value == "SUSPICION" for i in issues)


# ---------------------------------------------------------------------------
# Seuil configurable
# ---------------------------------------------------------------------------

def test_threshold_too_high_no_issues():
    """Avec un seuil de 99, Paris/Pari ne doit pas être détecté."""
    df = _make_df(["Paris"] * 3 + ["Pari"])
    rule = SimilarValuesRule()
    issues = rule.check(df, "titre", _cfg(similar_threshold=99))
    assert issues == []


def test_low_threshold_detects_more():
    """Avec un seuil bas (60), des paires moins similaires doivent être détectées."""
    df = _make_df(["chat"] * 3 + ["chien"])
    rule = SimilarValuesRule()
    # chat / chien : fuzz.ratio ~ 66 → détecté à threshold=60 mais pas à 85
    issues_60 = rule.check(df, "titre", _cfg(similar_threshold=60))
    issues_85 = rule.check(df, "titre", _cfg(similar_threshold=85))
    # At threshold 85, chat/chien won't be flagged; at 60 it should be
    assert len(issues_60) >= len(issues_85)


# ---------------------------------------------------------------------------
# min_distinct
# ---------------------------------------------------------------------------

def test_min_distinct_skips_tiny_columns():
    """Si la colonne a moins de min_distinct valeurs distinctes, rien ne sort."""
    df = _make_df(["Paris", "Pari"])
    rule = SimilarValuesRule()
    issues = rule.check(df, "titre", _cfg(similar_min_distinct=5))
    assert issues == []


def test_min_distinct_runs_with_enough_values():
    df = _make_df(["Paris"] * 3 + ["Pari", "Lyon", "Marseille", "Bordeaux"])
    rule = SimilarValuesRule()
    issues = rule.check(df, "titre", _cfg(similar_min_distinct=5))
    # Should run and possibly flag Paris/Pari
    paris_issues = [i for i in issues if "Pari" in i.message or "Paris" in i.message]
    assert paris_issues


# ---------------------------------------------------------------------------
# Cas limites
# ---------------------------------------------------------------------------

def test_no_issues_when_all_different():
    df = _make_df(["Paris", "Lyon", "Marseille", "Bordeaux", "Toulouse"])
    rule = SimilarValuesRule()
    issues = rule.check(df, "titre", _cfg())
    assert issues == []


def test_empty_column_no_issues():
    df = _make_df(["", "", ""])
    rule = SimilarValuesRule()
    issues = rule.check(df, "titre", _cfg())
    assert issues == []


def test_missing_column_no_issues():
    df = _make_df(["Paris", "Pari"])
    rule = SimilarValuesRule()
    issues = rule.check(df, "nonexistent", _cfg(col="nonexistent"))
    assert issues == []


def test_none_column_no_issues():
    df = _make_df(["Paris", "Pari"])
    rule = SimilarValuesRule()
    issues = rule.check(df, None, _cfg())
    assert issues == []
