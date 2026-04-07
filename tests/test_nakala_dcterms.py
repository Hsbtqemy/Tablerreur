"""Tests pour les champs dcterms dans les overlays NAKALA.

Couvre :
  - La config résultante contient les règles d'hygiène génériques
  - Les colonnes nakala:* obligatoires restent requises
  - Les colonnes dcterms:* recommandées sont configurées dans nakala_extended
  - dcterms:type avec valeur "article" génère une issue avec suggestion URI COAR
  - dcterms:description est bien marquée multiline_ok
  - dcterms:format valide un type MIME
  - dcterms:available valide un format W3C-DTF
"""
from __future__ import annotations

import pandas as pd
import pytest

from spreadsheet_qa.core.template_manager import TemplateManager


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _compile(overlay_id: str, column_names: list[str] | None = None) -> dict:
    mgr = TemplateManager()
    return mgr.compile_config(
        generic_id="generic_default",
        overlay_id=overlay_id,
        column_names=column_names or [],
    )


class _MockNakalaClient:
    """Client NAKALA simulé pour les tests de règles nakala.*."""
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


# 29 URIs COAR acceptées par NAKALA (snapshot baseline)
COAR_URIS = [
    "http://purl.org/coar/resource_type/c_c513",
    "http://purl.org/coar/resource_type/c_12ce",
    "http://purl.org/coar/resource_type/c_18cc",
    "http://purl.org/coar/resource_type/c_6501",
    "http://purl.org/coar/resource_type/c_6670",
    "http://purl.org/coar/resource_type/c_c94f",
    "http://purl.org/coar/resource_type/c_e059",
    "http://purl.org/coar/resource_type/c_2f33",
    "http://purl.org/coar/resource_type/c_12cd",
    "http://purl.org/coar/resource_type/c_ddb1",
    "http://purl.org/coar/resource_type/c_5ce6",
    "http://purl.org/coar/resource_type/c_1843",
    "http://purl.org/coar/resource_type/YC9F-HGCF",
    "http://purl.org/coar/resource_type/F8RT-TJK0",
    "http://purl.org/coar/resource_type/c_86bc",
    "http://purl.org/coar/resource_type/c_ba08",
    "http://purl.org/coar/resource_type/c_0040",
    "http://purl.org/coar/resource_type/c_0857",
    "http://purl.org/coar/resource_type/c_93fc",
    "http://purl.org/coar/resource_type/c_2fe3",
    "http://purl.org/coar/resource_type/c_816b",
    "http://purl.org/coar/resource_type/c_efa0",
    "http://purl.org/coar/resource_type/c_18cw",
    "http://purl.org/coar/resource_type/NHD0-W6SY",
    "http://purl.org/coar/resource_type/c_18cf",
    "http://purl.org/coar/resource_type/c_46ec",
    "http://purl.org/coar/resource_type/c_7ad9",
    "http://purl.org/coar/resource_type/c_beb9",
    "http://purl.org/coar/resource_type/c_e9a0",
]


# ---------------------------------------------------------------------------
# 1. Config résultante — règles d'hygiène génériques
# ---------------------------------------------------------------------------

def test_extended_config_has_hygiene_rules():
    """La config nakala_extended doit activer les règles d'hygiène génériques."""
    cfg = _compile("nakala_extended")
    rules = cfg.get("rules", {})
    assert rules.get("generic.hygiene.leading_trailing_space", {}).get("enabled"), (
        "generic.hygiene.leading_trailing_space doit être activée"
    )


def test_baseline_config_has_hygiene_rules():
    """La config nakala_baseline doit aussi activer les règles d'hygiène."""
    cfg = _compile("nakala_baseline")
    rules = cfg.get("rules", {})
    assert rules.get("generic.hygiene.leading_trailing_space", {}).get("enabled")


# ---------------------------------------------------------------------------
# 2. Colonnes nakala:* obligatoires toujours requises
# ---------------------------------------------------------------------------

NAKALA_REQUIRED = [
    "nakala:type", "nakala:title", "nakala:creator", "nakala:created", "nakala:license",
]


@pytest.mark.parametrize("col", NAKALA_REQUIRED)
def test_baseline_required_columns_still_required(col):
    """nakala_baseline : les 5 colonnes nakala:* restent obligatoires."""
    cfg = _compile("nakala_baseline", column_names=NAKALA_REQUIRED)
    col_cfg = cfg.get("columns", {})
    assert col in col_cfg, f"{col} doit être dans la config"
    assert col_cfg[col].get("required") is True, f"{col} doit être required=True"


@pytest.mark.parametrize("col", NAKALA_REQUIRED)
def test_extended_required_columns_still_required(col):
    """nakala_extended : les 5 colonnes nakala:* restent obligatoires."""
    cfg = _compile("nakala_extended", column_names=NAKALA_REQUIRED)
    col_cfg = cfg.get("columns", {})
    assert col in col_cfg
    assert col_cfg[col].get("required") is True


# ---------------------------------------------------------------------------
# 3. Colonnes dcterms:* recommandées présentes dans nakala_extended
# ---------------------------------------------------------------------------

DCTERMS_RECOMMENDED = [
    "dcterms:type", "dcterms:title", "dcterms:creator", "dcterms:created",
    "dcterms:license", "dcterms:description", "dcterms:language", "dcterms:subject",
    "dcterms:publisher", "dcterms:contributor", "dcterms:rights", "dcterms:rightsHolder",
    "dcterms:relation", "dcterms:source", "dcterms:spatial",
    "dcterms:available", "dcterms:modified", "dcterms:format", "dcterms:abstract",
    "dcterms:mediator",
]


@pytest.mark.parametrize("col", DCTERMS_RECOMMENDED)
def test_extended_has_dcterms_columns(col):
    """nakala_extended : toutes les colonnes dcterms:* recommandées ont une config."""
    all_cols = NAKALA_REQUIRED + DCTERMS_RECOMMENDED
    cfg = _compile("nakala_extended", column_names=all_cols)
    col_cfg = cfg.get("columns", {})
    assert col in col_cfg, f"{col} doit être dans la config de nakala_extended"


def test_extended_dcterms_columns_not_required():
    """nakala_extended : les colonnes dcterms:* ne doivent PAS être required."""
    all_cols = NAKALA_REQUIRED + DCTERMS_RECOMMENDED
    cfg = _compile("nakala_extended", column_names=all_cols)
    col_cfg = cfg.get("columns", {})
    for col in DCTERMS_RECOMMENDED:
        assert not col_cfg.get(col, {}).get("required"), (
            f"{col} ne doit pas être required dans nakala_extended"
        )


def test_extended_dcterms_description_is_multiline():
    """dcterms:description doit avoir multiline_ok=True."""
    cfg = _compile("nakala_extended", column_names=["dcterms:description"])
    col_cfg = cfg.get("columns", {})
    assert col_cfg.get("dcterms:description", {}).get("multiline_ok") is True


def test_extended_dcterms_abstract_is_multiline():
    """dcterms:abstract doit avoir multiline_ok=True."""
    cfg = _compile("nakala_extended", column_names=["dcterms:abstract"])
    col_cfg = cfg.get("columns", {})
    assert col_cfg.get("dcterms:abstract", {}).get("multiline_ok") is True


# ---------------------------------------------------------------------------
# 4. dcterms:type avec "article" → issue avec suggestion URI COAR
# ---------------------------------------------------------------------------

def test_dcterms_type_article_gives_uri_suggestion():
    """dcterms:type = 'article' doit générer une issue avec suggestion URI COAR.

    Ce test appelle directement NakalaDepositTypeRule avec la config de dcterms:type.
    """
    from spreadsheet_qa.core.rules.nakala_rules import NakalaDepositTypeRule

    rule = NakalaDepositTypeRule()
    client = _MockNakalaClient(deposit_types=COAR_URIS)

    df = pd.DataFrame({"dcterms:type": pd.array(["article"], dtype="object")})
    issues = rule.check(df, "dcterms:type", {"_nakala_client": client})

    assert len(issues) == 1, "Une issue doit être générée pour 'article'"
    issue = issues[0]
    # Le message doit indiquer que c'est un libellé reconnu
    assert "reconnu" in issue.message.lower(), (
        f"Le message devrait mentionner 'reconnu', obtenu : {issue.message!r}"
    )
    # La suggestion doit être l'URI COAR de l'article de journal
    assert issue.suggestion == "http://purl.org/coar/resource_type/c_6501", (
        f"Suggestion attendue : URI c_6501, obtenu : {issue.suggestion!r}"
    )


def test_dcterms_type_valid_uri_no_issue():
    """dcterms:type avec une URI COAR valide ne doit pas générer d'issue."""
    from spreadsheet_qa.core.rules.nakala_rules import NakalaDepositTypeRule

    rule = NakalaDepositTypeRule()
    client = _MockNakalaClient(deposit_types=COAR_URIS)

    valid_uri = "http://purl.org/coar/resource_type/c_6501"
    df = pd.DataFrame({"dcterms:type": pd.array([valid_uri], dtype="object")})
    issues = rule.check(df, "dcterms:type", {"_nakala_client": client})
    assert issues == []


def test_dcterms_type_jeu_de_donnees_suggests_c_ddb1():
    """'Jeu de données' dans dcterms:type → suggestion URI c_ddb1."""
    from spreadsheet_qa.core.rules.nakala_rules import NakalaDepositTypeRule

    rule = NakalaDepositTypeRule()
    client = _MockNakalaClient(deposit_types=COAR_URIS)

    df = pd.DataFrame({"dcterms:type": pd.array(["Jeu de données"], dtype="object")})
    issues = rule.check(df, "dcterms:type", {"_nakala_client": client})

    assert len(issues) == 1
    assert issues[0].suggestion == "http://purl.org/coar/resource_type/c_ddb1"


# ---------------------------------------------------------------------------
# 5. Validation avec un DataFrame complet (nakala:* + dcterms:*)
# ---------------------------------------------------------------------------

def test_full_validation_nakala_and_dcterms_columns():
    """Validation d'un DataFrame avec colonnes nakala:* et dcterms:*.

    - Colonnes nakala:* valides → règles génériques actives
    - dcterms:description multiligne → ok
    - dcterms:format MIME valide → ok
    - dcterms:available date W3C-DTF valide → ok
    """
    from spreadsheet_qa.core.engine import ValidationEngine

    columns = NAKALA_REQUIRED + [
        "dcterms:description", "dcterms:format", "dcterms:available"
    ]
    cfg = _compile("nakala_extended", column_names=columns)

    df = pd.DataFrame({
        "nakala:type":    pd.array(["http://purl.org/coar/resource_type/c_6501"], dtype="object"),
        "nakala:title":   pd.array(["Titre valide"], dtype="object"),
        "nakala:creator": pd.array(["Dupont, Jean"], dtype="object"),
        "nakala:created": pd.array(["2024"], dtype="object"),
        "nakala:license": pd.array(["CC-BY-4.0"], dtype="object"),
        "dcterms:description": pd.array(["Description\nsur plusieurs\nlignes"], dtype="object"),
        "dcterms:format": pd.array(["application/pdf"], dtype="object"),
        "dcterms:available": pd.array(["2025-01"], dtype="object"),
    })

    engine = ValidationEngine()
    issues = engine.validate(df, config=cfg).issues

    # Pas d'issues sur les colonnes dcterms valides
    dcterms_issues = [i for i in issues if i.col and i.col.startswith("dcterms:")]
    assert dcterms_issues == [], (
        f"Les colonnes dcterms:* valides ne doivent pas générer d'issues, "
        f"obtenu : {dcterms_issues}"
    )


def test_validation_dcterms_format_invalid_mime():
    """dcterms:format avec valeur non-MIME doit générer une issue generic.regex."""
    from spreadsheet_qa.core.engine import ValidationEngine

    columns = NAKALA_REQUIRED + ["dcterms:format"]
    cfg = _compile("nakala_extended", column_names=columns)

    df = pd.DataFrame({
        "nakala:type":    pd.array(["http://purl.org/coar/resource_type/c_6501"], dtype="object"),
        "nakala:title":   pd.array(["Titre"], dtype="object"),
        "nakala:creator": pd.array(["Nom, Prénom"], dtype="object"),
        "nakala:created": pd.array(["2024"], dtype="object"),
        "nakala:license": pd.array(["CC-BY-4.0"], dtype="object"),
        "dcterms:format": pd.array(["PDF (invalide)"], dtype="object"),
    })

    engine = ValidationEngine()
    issues = engine.validate(df, config=cfg).issues
    format_issues = [i for i in issues if i.col == "dcterms:format"]
    assert len(format_issues) >= 1, (
        "dcterms:format avec valeur non-MIME doit générer au moins une issue"
    )


# ---------------------------------------------------------------------------
# 6. dcterms:type dans nakala_extended a les 29 URIs COAR
# ---------------------------------------------------------------------------

def test_extended_dcterms_type_has_29_allowed_values():
    """dcterms:type dans nakala_extended doit avoir les 29 URIs COAR."""
    cfg = _compile("nakala_extended", column_names=["dcterms:type"])
    col_cfg = cfg.get("columns", {})
    avs = col_cfg.get("dcterms:type", {}).get("allowed_values", [])
    assert len(avs) == 29, f"29 URIs COAR attendues, {len(avs)} trouvées"
    for uri in COAR_URIS:
        assert uri in avs, f"{uri} doit être dans dcterms:type allowed_values"


def test_extended_dcterms_type_is_locked():
    """dcterms:type dans nakala_extended doit être verrouillé (allowed_values_locked)."""
    cfg = _compile("nakala_extended", column_names=["dcterms:type"])
    col_cfg = cfg.get("columns", {})
    assert col_cfg.get("dcterms:type", {}).get("allowed_values_locked") is True
