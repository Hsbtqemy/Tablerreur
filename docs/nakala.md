# NAKALA Overlay

## Overview

The NAKALA overlay adds field-specific validation rules for datasets intended for
deposit in the [NAKALA](https://nakala.fr) research data repository.

Enable it via: **Templates… → Apply template → Overlay → NAKALA Baseline or Extended**.

**Référence complète (validation / formats acceptés) :** voir **[docs/nakala-validation-formats.md](nakala-validation-formats.md)** — 5 propriétés NAKALA obligatoires, dcterms, encodages (W3CDTF, LCSH, Box, Point, etc.), relations DataCite (RelationType), vocabulaires API (`/vocabularies/properties`, `/vocabularies/metadatatypes`, etc.), spécificité collections.

## Required NAKALA fields

| Field | Kind | Rule |
|-------|------|------|
| `nakala:type` | controlled | Must match COAR deposit types from API |
| `nakala:title` | free_text_short | Required, non-empty |
| `nakala:creator` | structured | Format: `Lastname, Firstname` |
| `nakala:created` | structured | W3C-DTF: `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` |
| `nakala:license` | controlled | Must match NAKALA license vocabulary |

## Recommended fields

| Field | Kind | Notes |
|-------|------|-------|
| `dcterms:description` | free_text_long | Multiline OK; `\|` allowed in text |
| `dcterms:subject` | list | Prefer repeated columns `keywords_*_1..n` |
| `dcterms:language` | controlled | RFC5646 code from API |

## Champs à intégrer (dcterms / alignement NAKALA)

### Vérification via la doc officielle NAKALA (documentation.huma-num.fr)

La description NAKALA repose sur **Dublin Core qualifié (dcterms)**. Outre les 5 champs obligatoires (Title, Author, Date, Type, License), il est possible d’ajouter **tout autre champ du vocabulaire Dublin Core qualifié**.

**Termes confirmés par le guide NAKALA :**
- **dcterms:creator** — explicitement cité (créateur ; peut compléter ou dupliquer le champ Author).
- **dcterms:contributor** — explicitement cité (« Other fields relate to the description of a role… »).
- **dcterms:publisher** — explicitement cité (éditeur).
- **dcterms:rightsHolder** — correspond au « rightsholder » du Dublin Core qualifié (cité dans les « additional headings » : audience, provenance, **rightsholder**).

**Terme à considérer (vocabulaire DC, non cité explicitement dans le guide) :**
- **dcterms:mediator** — entité qui médiatise l’accès à la ressource (ex. enseignant pour une ressource pédagogique) ; terme valide en dcterms, à intégrer si besoin métier.

**Autres champs dcterms mentionnés ou utiles** (non encore dans nos templates) :  
dcterms:alternative (titre secondaire), dcterms:tableOfContents (sommaire), dcterms:abstract (résumé), dcterms:coverage (couverture), dcterms:provenance, dcterms:audience, et les qualificateurs de date (available, modified, issued, etc.). La liste complète est celle du [qualified Dublin Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/).

À prendre en compte dans les templates ou la config NAKALA :

- **dcterms:creator**
- **dcterms:contributor**
- **dcterms:mediator** (optionnel, selon besoin)
- **dcterms:publisher**
- **dcterms:rightsHolder**

Référence **schéma d’export NAKALA** (colonnes possibles, avec préfixes `nakala.fr/terms#` ou `purl.org/dc/terms/`) :

| Colonne / URI | Note |
|---------------|------|
| DOI, Status donnee | Métadonnées dépôt |
| http://nakala.fr/terms#title, langTitle | Titre(s) |
| http://nakala.fr/terms#creator | Créateur |
| http://nakala.fr/terms#created | Date création |
| http://nakala.fr/terms#type | Type COAR |
| http://nakala.fr/terms#license | Licence |
| Embargoed | Embargo |
| http://purl.org/dc/terms/created | dcterms:created |
| http://purl.org/dc/terms/creator | dcterms:creator |
| http://purl.org/dc/terms/contributor | dcterms:contributor |
| http://purl.org/dc/terms/description, langDescription | Description(s) |
| http://purl.org/dc/terms/language | Langue |
| http://purl.org/dc/terms/relation | Relation(s) |
| http://purl.org/dc/terms/rightsHolder | Titulaire des droits |
| http://purl.org/dc/terms/spatial | Couverture spatiale |
| http://purl.org/dc/terms/available | Disponibilité |
| http://purl.org/dc/terms/modified | Date modification |
| http://purl.org/dc/terms/rights | Droits |
| http://purl.org/dc/terms/isVersionOf | Version de |
| http://purl.org/dc/terms/format | Format |
| http://purl.org/dc/terms/bibliographicCitation | Citation |
| http://purl.org/dc/terms/abstract | Résumé |
| http://purl.org/dc/terms/source | Source |
| http://purl.org/dc/terms/subject, langSubject | Sujet(s) |
| http://purl.org/dc/terms/medium | Support |
| http://purl.org/dc/terms/publisher | Éditeur |
| dcterms:mediator | Optionnel (médiateur ; dcterms valide, non cité explicitement dans le guide NAKALA) |
| IsDescribedBy, IsIdenticalTo, IsDerivedFrom, IsPublishedIn | Relations |
| sha1:files_to_delete, files_names_to_add, new_collectionsIds, collectionsIdsToDelete | Gestion technique dépôt |

Les templates actuels utilisent des noms courts (`nakala:creator`, `dcterms:description`). Un mapping ou des alias vers les URIs complètes (`http://purl.org/dc/terms/creator`, etc.) peuvent être nécessaires pour l’export / l’alignement avec l’API NAKALA.

## API vocabulary sources

Vocabularies sont récupérés via l’API NAKALA et mis en cache dans `nakala_cache.json`. Vérification 2026 : les endpoints ci‑dessous répondent (demander `Accept: application/json` pour le JSON). La fiche [nakala-validation-formats.md](nakala-validation-formats.md) détaille la règle « propriété ∈ properties, type ∈ metadatatypes ».

**Utilisés actuellement par Tablerreur :**

| Vocab | Endpoint | Réponse |
|-------|----------|---------|
| Types de ressource (COAR) | `https://api.nakala.fr/vocabularies/datatypes` | Liste d’URIs COAR. Le [guide NAKALA](https://documentation.huma-num.fr/en/nakala-guide-de-description-en/) fournit le **mapping libellé → URI** (image, video, sound, text, dataset, etc.) pour affichage utilisateur. |
| Licences | `https://api.nakala.fr/vocabularies/licenses` | `[{"code": "CC-BY-4.0", "name": "..."}, ...]` |
| Langues | `https://api.nakala.fr/vocabularies/languages?limit=10000` | `[{"id": "fra", "label": "..."}, ...]` |

**Endpoints recommandés par la fiche validation (à intégrer si besoin) :**

| Vocab | Endpoint | Usage |
|-------|----------|--------|
| Propriétés acceptées | `/vocabularies/properties` (+ `.../details`) | Valider que toute propriété dcterms utilisée est acceptée ; types/encodages par propriété. |
| Types/encodages métadonnées | `/vocabularies/metadatatypes` (+ `.../details`) | W3CDTF, URI, LCSH, TGN, Box, Point, Period, ISO3166, RFC5646, DCMIType, etc. |
| Types DCMI | `/vocabularies/dcmitypes` | dcterms:type (Collection, Dataset, Image, Text, …). |
| Codes pays | `/vocabularies/countryCodes` | dcterms:spatial / subject (ISO3166). |
| LCSH | `/vocabularies/lcsh` | dcterms:subject (Library of Congress). |
| Statuts | `/vocabularies/dataStatuses`, `/vocabularies/collectionStatuses` | Statut donnée ; collections : privé/public. |

## Separator policy

- `|` is the multi-value in-cell separator for the tool.
- For NAKALA `description` fields: `|` is allowed as text content (not interpreted as list separator).
- For repeatable fields (`nakala:creator`, `dcterms:subject`): using `|` in-cell triggers a **WARNING** with a suggestion to split to repeated columns.
- Export in NAKALA mode defaults to `multivalues_mode: expanded` (columns `creator_1`, `creator_2`, …).

## Baseline vs Extended comparison

| Feature | NAKALA Baseline | NAKALA Extended |
|---------|----------------|-----------------|
| Required columns (5) | ✅ | ✅ |
| `nakala.deposit_type` rule | ✅ | ✅ |
| `nakala.license` rule | ✅ | ✅ |
| `nakala.created_format` rule | ✅ | ✅ |
| `nakala.language` rule | — | ✅ |
| Recommended fields (`dcterms:*`) | — | ✅ |
| Multilingual column groups (`title_*`) | — | ✅ |
| Keyword columns (`keywords_*`) | — | ✅ |
| Creator format structured check | — | ✅ |
| Identifier/relation URI columns | — | ✅ |

## rule_overrides example

In a template YAML you can override a specific rule for a specific column:

```yaml
columns:
  "nakala:title":
    kind: free_text_short
    required: true
    rule_overrides:
      generic.pseudo_missing:
        enabled: true
        severity: ERROR    # escalate from WARNING to ERROR for this column
      generic.soft_typing:
        enabled: false     # disable soft typing for this column entirely
```

The `rule_overrides` block is per-column and per-rule. It does NOT affect
other columns. The engine applies: `base_rule_config < col_meta < rule_override`.

## Column mapping wizard

The Template Library (Templates… toolbar button) lets you:
1. Select a base template (Generic Default or Generic Strict).
2. Select an overlay (NAKALA Baseline or NAKALA Extended).
3. Apply & Validate — immediately runs validation with the new config.

Column-to-field mapping is handled in the Template Editor (Edit… button):
- Select the column in the left pane.
- Set `kind: controlled` and optionally `preset` for structured formats.
- Rule overrides can disable/escalate specific rules per column.

Vocabulary fetching from the NAKALA API is handled transparently:
- Vocabularies are fetched once and cached to `nakala_cache.json`.
- If offline: vocabulary-based rules (`nakala.deposit_type`, `nakala.license`,
  `nakala.language`) skip silently (no false positives).
- `nakala.created_format` is purely regex-based and works offline.

## Backlog — libellés et champs dcterms

- **Transformation libellé → URI** : aujourd’hui les vocabulaires NAKALA (types COAR, licences SPDX, langues) attendent des **valeurs canoniques** (URIs ou codes), pas des libellés (« texte », « image »). Idée : permettre de saisir un libellé et de le convertir en URI (correctif ou mapping), avec un dictionnaire libellé (FR/EN) → URI.
- **Type selon le champ dcterms/nakala** : en config de colonne, pouvoir choisir « Cette colonne = nakala:type » (ou dcterms:type, nakala:license, dcterms:language, etc.) pour que l’interface applique automatiquement le bon vocabulaire et la bonne règle, avec éventuellement une liste déroulante libellé/URI. Voir BACKLOG.md §7.
