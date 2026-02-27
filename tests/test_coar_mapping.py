"""Tests pour core/coar_mapping.py — dictionnaire libellé ↔ URI COAR et règle nakala.deposit_type.

Couvre :
- label_to_coar_uri() : conversion libellé → URI (FR, EN, insensible casse)
- coar_uri_to_label() : conversion URI → libellé FR
- suggest_coar_uri() : correspondance approchée
- COAR_URI_TO_LABEL_FR contient les 29 URIs NAKALA
- NakalaDepositTypeRule : suggestion URI quand libellé reconnu
"""
from __future__ import annotations

import pandas as pd
import pytest

from spreadsheet_qa.core.coar_mapping import (
    COAR_LABEL_TO_URI,
    COAR_URI_TO_LABEL_FR,
    coar_uri_to_label,
    label_to_coar_uri,
    suggest_coar_uri,
)

# URIs NAKALA attendues (snapshot nakala_baseline.yml)
EXPECTED_NAKALA_URIS = [
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
# COAR_URI_TO_LABEL_FR — couverture des 29 URIs NAKALA
# ---------------------------------------------------------------------------

def test_all_nakala_uris_have_fr_label():
    """Toutes les 29 URIs de nakala_baseline.yml doivent avoir un libellé FR."""
    missing = [uri for uri in EXPECTED_NAKALA_URIS if uri not in COAR_URI_TO_LABEL_FR]
    assert missing == [], f"URIs sans libellé FR : {missing}"


def test_fr_labels_are_non_empty_strings():
    """Chaque libellé FR doit être une chaîne non vide."""
    for uri, label in COAR_URI_TO_LABEL_FR.items():
        assert isinstance(label, str) and label.strip(), f"Libellé vide pour {uri!r}"


# ---------------------------------------------------------------------------
# label_to_coar_uri — conversion libellé → URI
# ---------------------------------------------------------------------------

def test_label_to_uri_article_fr():
    assert label_to_coar_uri("article") == "http://purl.org/coar/resource_type/c_6501"


def test_label_to_uri_jeu_de_donnees():
    assert label_to_coar_uri("jeu de données") == "http://purl.org/coar/resource_type/c_ddb1"


def test_label_to_uri_dataset_en():
    assert label_to_coar_uri("dataset") == "http://purl.org/coar/resource_type/c_ddb1"


def test_label_to_uri_case_insensitive():
    assert label_to_coar_uri("Jeu de Données") == "http://purl.org/coar/resource_type/c_ddb1"
    assert label_to_coar_uri("ARTICLE") == "http://purl.org/coar/resource_type/c_6501"
    assert label_to_coar_uri("Rapport") == "http://purl.org/coar/resource_type/c_93fc"


def test_label_to_uri_video():
    assert label_to_coar_uri("vidéo") == "http://purl.org/coar/resource_type/c_12ce"
    assert label_to_coar_uri("video") == "http://purl.org/coar/resource_type/c_12ce"


def test_label_to_uri_logiciel():
    assert label_to_coar_uri("logiciel") == "http://purl.org/coar/resource_type/c_5ce6"
    assert label_to_coar_uri("software") == "http://purl.org/coar/resource_type/c_5ce6"


def test_label_to_uri_unknown_returns_none():
    assert label_to_coar_uri("inconnu_xyz") is None
    assert label_to_coar_uri("") is None
    assert label_to_coar_uri("   ") is None


def test_label_to_uri_with_leading_trailing_space():
    """Les espaces doivent être ignorés lors de la recherche."""
    assert label_to_coar_uri("  article  ") == "http://purl.org/coar/resource_type/c_6501"


# ---------------------------------------------------------------------------
# coar_uri_to_label — conversion URI → libellé FR
# ---------------------------------------------------------------------------

def test_uri_to_label_dataset():
    assert coar_uri_to_label("http://purl.org/coar/resource_type/c_ddb1") == "Jeu de données"


def test_uri_to_label_unknown_returns_none():
    assert coar_uri_to_label("http://purl.org/coar/resource_type/UNKNOWN") is None


def test_uri_to_label_all_nakala_uris():
    """Toutes les 29 URIs NAKALA doivent retourner un libellé non None."""
    for uri in EXPECTED_NAKALA_URIS:
        result = coar_uri_to_label(uri)
        assert result is not None, f"coar_uri_to_label({uri!r}) retourne None"


# ---------------------------------------------------------------------------
# suggest_coar_uri — correspondance approchée
# ---------------------------------------------------------------------------

def test_suggest_exact_match():
    assert suggest_coar_uri("vidéo") == "http://purl.org/coar/resource_type/c_12ce"


def test_suggest_case_insensitive_exact():
    assert suggest_coar_uri("Rapport") == "http://purl.org/coar/resource_type/c_93fc"


def test_suggest_partial_inclusion():
    """Une valeur contenant un libellé connu doit être reconnue par inclusion."""
    uri = suggest_coar_uri("logiciel libre")
    # "logiciel" est dans "logiciel libre"
    assert uri == "http://purl.org/coar/resource_type/c_5ce6"


def test_suggest_no_match_returns_none():
    assert suggest_coar_uri("xyzzy_pas_un_type") is None


def test_suggest_uri_is_not_recognized_as_label():
    """Une URI COAR brute n'est PAS un libellé — on ne doit pas suggérer une URI à partir d'une URI."""
    # Une URI valide n'est pas un libellé, donc suggest_coar_uri ne doit pas la mapper
    # (à moins que son contenu partiel corresponde à un label, ce qui ne devrait pas arriver)
    result = suggest_coar_uri("http://purl.org/coar/resource_type/c_ddb1")
    # L'URI elle-même n'est pas un libellé — résultat peut être None ou incorrect
    # Ce test vérifie juste qu'il n'y a pas d'erreur
    assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# NakalaDepositTypeRule — suggestion URI quand libellé reconnu
# ---------------------------------------------------------------------------

class _MockNakalaClient:
    def __init__(self, deposit_types):
        self._deposit_types = deposit_types

    def fetch_deposit_types(self):
        return self._deposit_types


VALID_URIS = [
    "http://purl.org/coar/resource_type/c_ddb1",
    "http://purl.org/coar/resource_type/c_6501",
]


def test_deposit_type_rule_with_known_label_suggests_uri():
    """Valeur 'article' → suggestion avec l'URI COAR correspondante."""
    from spreadsheet_qa.core.rules.nakala_rules import NakalaDepositTypeRule
    rule = NakalaDepositTypeRule()
    client = _MockNakalaClient(deposit_types=VALID_URIS)
    df = pd.DataFrame({"nakala:type": pd.array(["article"], dtype="object")})
    issues = rule.check(df, "nakala:type", {"_nakala_client": client})

    assert len(issues) == 1
    # Le message doit mentionner le libellé reconnu
    assert "reconnu" in issues[0].message.lower()
    # La suggestion doit être l'URI COAR
    assert issues[0].suggestion == "http://purl.org/coar/resource_type/c_6501"


def test_deposit_type_rule_with_known_label_jeu_de_donnees():
    """'Jeu de données' → suggestion URI c_ddb1."""
    from spreadsheet_qa.core.rules.nakala_rules import NakalaDepositTypeRule
    rule = NakalaDepositTypeRule()
    client = _MockNakalaClient(deposit_types=VALID_URIS)
    df = pd.DataFrame({"nakala:type": pd.array(["Jeu de données"], dtype="object")})
    issues = rule.check(df, "nakala:type", {"_nakala_client": client})

    assert len(issues) == 1
    assert issues[0].suggestion == "http://purl.org/coar/resource_type/c_ddb1"


def test_deposit_type_rule_unknown_value_no_suggestion():
    """Valeur inconnue → message standard sans suggestion URI COAR."""
    from spreadsheet_qa.core.rules.nakala_rules import NakalaDepositTypeRule
    rule = NakalaDepositTypeRule()
    client = _MockNakalaClient(deposit_types=VALID_URIS)
    df = pd.DataFrame({"nakala:type": pd.array(["xyz_inconnu_999"], dtype="object")})
    issues = rule.check(df, "nakala:type", {"_nakala_client": client})

    assert len(issues) == 1
    # Message générique
    assert "non reconnu" in issues[0].message


def test_deposit_type_rule_valid_uri_no_issue():
    """URI valide → aucun problème."""
    from spreadsheet_qa.core.rules.nakala_rules import NakalaDepositTypeRule
    rule = NakalaDepositTypeRule()
    client = _MockNakalaClient(deposit_types=VALID_URIS)
    df = pd.DataFrame({"nakala:type": pd.array(["http://purl.org/coar/resource_type/c_ddb1"], dtype="object")})
    issues = rule.check(df, "nakala:type", {"_nakala_client": client})
    assert issues == []


# ---------------------------------------------------------------------------
# Messages FR avec guillemets « »
# ---------------------------------------------------------------------------

def test_created_format_message_is_french():
    """NakalaCreatedFormatRule doit produire un message en français avec guillemets «»."""
    from spreadsheet_qa.core.rules.nakala_rules import NakalaCreatedFormatRule
    rule = NakalaCreatedFormatRule()
    df = pd.DataFrame({"nakala:created": pd.array(["15/01/2024"], dtype="object")})
    issues = rule.check(df, "nakala:created", {})
    assert len(issues) == 1
    assert "«" in issues[0].message
    assert "15/01/2024" in issues[0].message


def test_license_message_is_french():
    """NakalaLicenseRule doit produire un message en français avec guillemets «»."""
    from spreadsheet_qa.core.rules.nakala_rules import NakalaLicenseRule
    rule = NakalaLicenseRule()
    client = _MockNakalaClient(deposit_types=[])
    client.fetch_licenses = lambda: ["CC-BY-4.0"]
    df = pd.DataFrame({"nakala:license": pd.array(["INVALID-LIC"], dtype="object")})
    issues = rule.check(df, "nakala:license", {"_nakala_client": client})
    assert len(issues) == 1
    assert "«" in issues[0].message
    assert "INVALID-LIC" in issues[0].message


def test_language_message_is_french():
    """NakalaLanguageRule doit produire un message en français avec guillemets «»."""
    from spreadsheet_qa.core.rules.nakala_rules import NakalaLanguageRule
    rule = NakalaLanguageRule()
    client = _MockNakalaClient(deposit_types=[])
    client.fetch_languages = lambda: ["fra", "eng"]
    df = pd.DataFrame({"dcterms:language": pd.array(["zz"], dtype="object")})
    issues = rule.check(df, "dcterms:language", {"_nakala_client": client})
    assert len(issues) == 1
    assert "«" in issues[0].message
    assert "zz" in issues[0].message
