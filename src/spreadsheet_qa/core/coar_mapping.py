"""Mapping bidirectionnel libellé ↔ URI COAR pour les types de ressource NAKALA.

Les 29 types de ressource COAR acceptés par NAKALA (snapshot 2026-02).
Source officielle : https://vocabularies.coar-repositories.org/resource_types/

Usage :
    from spreadsheet_qa.core.coar_mapping import label_to_coar_uri, coar_uri_to_label, suggest_coar_uri
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# URI → libellé FR
# ---------------------------------------------------------------------------

COAR_URI_TO_LABEL_FR: dict[str, str] = {
    "http://purl.org/coar/resource_type/c_c513": "Image fixe",
    "http://purl.org/coar/resource_type/c_12ce": "Vidéo",
    "http://purl.org/coar/resource_type/c_18cc": "Enregistrement sonore",
    "http://purl.org/coar/resource_type/c_6501": "Article de journal",
    "http://purl.org/coar/resource_type/c_6670": "Poster",
    "http://purl.org/coar/resource_type/c_c94f": "Communication de conférence",
    "http://purl.org/coar/resource_type/c_e059": "Thèse de doctorat",
    "http://purl.org/coar/resource_type/c_2f33": "Livre",
    "http://purl.org/coar/resource_type/c_12cd": "Carte géographique",
    "http://purl.org/coar/resource_type/c_ddb1": "Jeu de données",
    "http://purl.org/coar/resource_type/c_5ce6": "Logiciel",
    "http://purl.org/coar/resource_type/c_1843": "Autre",
    "http://purl.org/coar/resource_type/YC9F-HGCF": "Revue",           # TODO: vérifier libellé officiel
    "http://purl.org/coar/resource_type/F8RT-TJK0": "Collection",      # TODO: vérifier libellé officiel
    "http://purl.org/coar/resource_type/c_86bc": "Préimpression",
    "http://purl.org/coar/resource_type/c_ba08": "Image en mouvement",
    "http://purl.org/coar/resource_type/c_0040": "Partie de livre",
    "http://purl.org/coar/resource_type/c_0857": "Actes de conférence",
    "http://purl.org/coar/resource_type/c_93fc": "Rapport",
    "http://purl.org/coar/resource_type/c_2fe3": "Mémoire de master",
    "http://purl.org/coar/resource_type/c_816b": "Article de synthèse",
    "http://purl.org/coar/resource_type/c_efa0": "Notice d'encyclopédie",
    "http://purl.org/coar/resource_type/c_18cw": "Entrée de dictionnaire",
    "http://purl.org/coar/resource_type/NHD0-W6SY": "Brevet",          # TODO: vérifier libellé officiel
    "http://purl.org/coar/resource_type/c_18cf": "Texte",
    "http://purl.org/coar/resource_type/c_46ec": "Manuscrit",
    "http://purl.org/coar/resource_type/c_7ad9": "Document de travail",
    "http://purl.org/coar/resource_type/c_beb9": "Communication",      # TODO: vérifier libellé officiel
    "http://purl.org/coar/resource_type/c_e9a0": "Revue critique",     # TODO: vérifier libellé officiel
}


# ---------------------------------------------------------------------------
# Libellé (FR/EN, insensible à la casse) → URI COAR
# ---------------------------------------------------------------------------

COAR_LABEL_TO_URI: dict[str, str] = {
    # ---- Image fixe ----
    "image fixe": "http://purl.org/coar/resource_type/c_c513",
    "image": "http://purl.org/coar/resource_type/c_c513",
    "still image": "http://purl.org/coar/resource_type/c_c513",
    "photographie": "http://purl.org/coar/resource_type/c_c513",
    "photograph": "http://purl.org/coar/resource_type/c_c513",

    # ---- Vidéo ----
    "vidéo": "http://purl.org/coar/resource_type/c_12ce",
    "video": "http://purl.org/coar/resource_type/c_12ce",

    # ---- Son ----
    "enregistrement sonore": "http://purl.org/coar/resource_type/c_18cc",
    "son": "http://purl.org/coar/resource_type/c_18cc",
    "audio": "http://purl.org/coar/resource_type/c_18cc",
    "sound": "http://purl.org/coar/resource_type/c_18cc",

    # ---- Article ----
    "article de journal": "http://purl.org/coar/resource_type/c_6501",
    "article": "http://purl.org/coar/resource_type/c_6501",
    "journal article": "http://purl.org/coar/resource_type/c_6501",

    # ---- Poster ----
    "poster": "http://purl.org/coar/resource_type/c_6670",
    "affiche": "http://purl.org/coar/resource_type/c_6670",

    # ---- Conférence ----
    "communication de conférence": "http://purl.org/coar/resource_type/c_c94f",
    "conférence": "http://purl.org/coar/resource_type/c_c94f",
    "conference paper": "http://purl.org/coar/resource_type/c_c94f",
    "conference output": "http://purl.org/coar/resource_type/c_c94f",

    # ---- Thèse de doctorat ----
    "thèse de doctorat": "http://purl.org/coar/resource_type/c_e059",
    "thèse": "http://purl.org/coar/resource_type/c_e059",
    "doctoral thesis": "http://purl.org/coar/resource_type/c_e059",
    "dissertation": "http://purl.org/coar/resource_type/c_e059",

    # ---- Livre ----
    "livre": "http://purl.org/coar/resource_type/c_2f33",
    "book": "http://purl.org/coar/resource_type/c_2f33",
    "ouvrage": "http://purl.org/coar/resource_type/c_2f33",

    # ---- Carte ----
    "carte géographique": "http://purl.org/coar/resource_type/c_12cd",
    "carte": "http://purl.org/coar/resource_type/c_12cd",
    "map": "http://purl.org/coar/resource_type/c_12cd",
    "cartographic map": "http://purl.org/coar/resource_type/c_12cd",

    # ---- Jeu de données ----
    "jeu de données": "http://purl.org/coar/resource_type/c_ddb1",
    "données": "http://purl.org/coar/resource_type/c_ddb1",
    "dataset": "http://purl.org/coar/resource_type/c_ddb1",
    "data": "http://purl.org/coar/resource_type/c_ddb1",

    # ---- Logiciel ----
    "logiciel": "http://purl.org/coar/resource_type/c_5ce6",
    "software": "http://purl.org/coar/resource_type/c_5ce6",
    "programme": "http://purl.org/coar/resource_type/c_5ce6",

    # ---- Autre ----
    "autre": "http://purl.org/coar/resource_type/c_1843",
    "other": "http://purl.org/coar/resource_type/c_1843",

    # ---- Revue ----
    "revue": "http://purl.org/coar/resource_type/YC9F-HGCF",
    "journal": "http://purl.org/coar/resource_type/YC9F-HGCF",
    "periodical": "http://purl.org/coar/resource_type/YC9F-HGCF",

    # ---- Collection ----
    "collection": "http://purl.org/coar/resource_type/F8RT-TJK0",

    # ---- Préimpression ----
    "préimpression": "http://purl.org/coar/resource_type/c_86bc",
    "preprint": "http://purl.org/coar/resource_type/c_86bc",
    "prépublication": "http://purl.org/coar/resource_type/c_86bc",

    # ---- Image en mouvement ----
    "image en mouvement": "http://purl.org/coar/resource_type/c_ba08",
    "moving image": "http://purl.org/coar/resource_type/c_ba08",
    "film": "http://purl.org/coar/resource_type/c_ba08",

    # ---- Partie de livre ----
    "partie de livre": "http://purl.org/coar/resource_type/c_0040",
    "chapitre de livre": "http://purl.org/coar/resource_type/c_0040",
    "chapitre": "http://purl.org/coar/resource_type/c_0040",
    "book part": "http://purl.org/coar/resource_type/c_0040",
    "book chapter": "http://purl.org/coar/resource_type/c_0040",
    "chapter": "http://purl.org/coar/resource_type/c_0040",

    # ---- Actes de conférence ----
    "actes de conférence": "http://purl.org/coar/resource_type/c_0857",
    "actes": "http://purl.org/coar/resource_type/c_0857",
    "conference proceedings": "http://purl.org/coar/resource_type/c_0857",
    "proceedings": "http://purl.org/coar/resource_type/c_0857",

    # ---- Rapport ----
    "rapport": "http://purl.org/coar/resource_type/c_93fc",
    "report": "http://purl.org/coar/resource_type/c_93fc",

    # ---- Mémoire de master ----
    "mémoire de master": "http://purl.org/coar/resource_type/c_2fe3",
    "mémoire": "http://purl.org/coar/resource_type/c_2fe3",
    "master thesis": "http://purl.org/coar/resource_type/c_2fe3",
    "master": "http://purl.org/coar/resource_type/c_2fe3",

    # ---- Article de synthèse ----
    "article de synthèse": "http://purl.org/coar/resource_type/c_816b",
    "review article": "http://purl.org/coar/resource_type/c_816b",
    "synthèse": "http://purl.org/coar/resource_type/c_816b",

    # ---- Notice d'encyclopédie ----
    "notice d'encyclopédie": "http://purl.org/coar/resource_type/c_efa0",
    "notice encyclopédie": "http://purl.org/coar/resource_type/c_efa0",
    "encyclopedia entry": "http://purl.org/coar/resource_type/c_efa0",
    "encyclopédie": "http://purl.org/coar/resource_type/c_efa0",

    # ---- Entrée de dictionnaire ----
    "entrée de dictionnaire": "http://purl.org/coar/resource_type/c_18cw",
    "entrée dictionnaire": "http://purl.org/coar/resource_type/c_18cw",
    "dictionary entry": "http://purl.org/coar/resource_type/c_18cw",
    "dictionnaire": "http://purl.org/coar/resource_type/c_18cw",

    # ---- Brevet ----
    "brevet": "http://purl.org/coar/resource_type/NHD0-W6SY",
    "patent": "http://purl.org/coar/resource_type/NHD0-W6SY",

    # ---- Texte ----
    "texte": "http://purl.org/coar/resource_type/c_18cf",
    "text": "http://purl.org/coar/resource_type/c_18cf",

    # ---- Manuscrit ----
    "manuscrit": "http://purl.org/coar/resource_type/c_46ec",
    "manuscript": "http://purl.org/coar/resource_type/c_46ec",

    # ---- Document de travail ----
    "document de travail": "http://purl.org/coar/resource_type/c_7ad9",
    "working paper": "http://purl.org/coar/resource_type/c_7ad9",
    "note de travail": "http://purl.org/coar/resource_type/c_7ad9",

    # ---- Communication ----
    "communication": "http://purl.org/coar/resource_type/c_beb9",

    # ---- Revue critique ----
    "revue critique": "http://purl.org/coar/resource_type/c_e9a0",
    "compte rendu": "http://purl.org/coar/resource_type/c_e9a0",
    "review": "http://purl.org/coar/resource_type/c_e9a0",
}


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def label_to_coar_uri(label: str) -> str | None:
    """Convertit un libellé FR/EN en URI COAR. Retourne None si non trouvé.

    La comparaison est insensible à la casse.
    """
    return COAR_LABEL_TO_URI.get(label.strip().lower())


def coar_uri_to_label(uri: str, lang: str = "fr") -> str | None:
    """Convertit une URI COAR en libellé lisible (français par défaut)."""
    return COAR_URI_TO_LABEL_FR.get(uri.strip())


def suggest_coar_uri(value: str) -> str | None:
    """Tente de trouver l'URI COAR la plus proche d'une valeur.

    1. Essai exact (insensible à la casse) dans COAR_LABEL_TO_URI.
    2. Essai par inclusion : le libellé contient la valeur, ou la valeur contient le libellé.
    Retourne None si aucune correspondance.
    """
    # Essai exact
    uri = label_to_coar_uri(value)
    if uri:
        return uri
    # Essai par inclusion
    lower = value.strip().lower()
    for label, uri in COAR_LABEL_TO_URI.items():
        if lower in label or label in lower:
            return uri
    return None
