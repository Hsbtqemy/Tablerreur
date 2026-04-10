# NAKALA — Correspondances suggérées depuis les noms de colonnes

Cette note décrit le petit référentiel utilisé par l’assistant de correspondance NAKALA dans l’étape **Configurer**.

Objectif :

- proposer des correspondances explicites quand le fichier source n’utilise pas déjà les noms exacts `nakala:*` ou `dcterms:*`
- ne jamais appliquer ces correspondances silencieusement
- garder un référentiel court, lisible et testable

Source de vérité exécutable :

- [src/spreadsheet_qa/web/static/nakala_template_match_helpers.js](c:/Dev/Tablerreur/src/spreadsheet_qa/web/static/nakala_template_match_helpers.js)

## Règles de fonctionnement

- Le matching commence par normaliser les noms de colonnes : minuscules, accents retirés, séparateurs convertis en espaces.
- Deux familles de cibles sont reconnues :
  - colonnes exactes du template, par exemple `nakala:title` ou `dcterms:language`
  - groupes de colonnes du template, par exemple `nakala:title_*`, `dcterms:description_*`, `keywords_*`
- Les suggestions restent **confirmables** par l’utilisateur.
- Une colonne déjà personnalisée manuellement reste visible comme suggestion, mais n’est pas appliquée automatiquement.

## Référentiel actuel

### Champs exacts

| Champ cible | Alias/motifs courants |
|---|---|
| `nakala:type` | `type`, `resource_type`, `document_type`, `genre`, `type_ressource` |
| `nakala:title` | `title`, `titre`, `main_title`, `resource_title` |
| `nakala:creator` | `creator`, `author`, `auteur`, `creator_name`, `author_name`, `auteur_principal` |
| `nakala:created` | `created`, `date_created`, `creation_date`, `date_creation`, `year`, `annee` |
| `nakala:license` | `license`, `licence`, `rights_license`, `licence_usage` |
| `dcterms:language` | `language`, `lang`, `langue`, `iso_lang`, `language_code`, `langue_notice` |
| `dcterms:description` | `description`, `desc`, `description_libre` |
| `dcterms:subject` | `subject`, `subjects`, `keyword`, `keywords`, `topic`, `sujet`, `mots_cles`, `tags` |
| `dcterms:publisher` | `publisher`, `editeur`, `editor` |
| `dcterms:contributor` | `contributor`, `contributors`, `contributor_name`, `coauthor`, `co_author` |
| `dcterms:rights` | `rights`, `droits`, `copyright`, `access_rights` |
| `dcterms:rightsHolder` | `rights_holder`, `copyright_holder`, `titulaire_droits`, `holder` |
| `dcterms:relation` | `relation`, `related_url`, `related_identifier`, `lien_associe` |
| `dcterms:source` | `source`, `provenance`, `origin`, `origine` |
| `dcterms:spatial` | `spatial`, `coverage`, `couverture_geo`, `location`, `lieu` |
| `dcterms:available` | `available`, `date_available`, `publication_date`, `date_publication` |
| `dcterms:modified` | `modified`, `last_modified`, `updated_at`, `date_modified` |
| `dcterms:format` | `format`, `mime_type`, `file_format`, `content_type` |
| `dcterms:abstract` | `abstract`, `resume`, `summary` |
| `dcterms:mediator` | `mediator`, `mediation`, `teacher`, `enseignant_referent` |
| `dcterms:identifier` | `identifier`, `identifier_uri`, `resource_identifier`, `uri`, `url`, `doi`, `ark` |

### Groupes et motifs

| Groupe cible | Motifs reconnus |
|---|---|
| `nakala:title_*` | `lang_title`, `title_lang`, `title_fr`, `title_en`, `titre_fr`, `titre_en`, `translated_title`, `alt_title` |
| `dcterms:description_*` | `description_fr`, `description_en`, `resume_fr`, `abstract_en` |
| `keywords_*` | `keywords_en_1`, `keywords_fr`, `mots_cles_fr_1`, `tags_en` |
| `dcterms:identifier*` | `identifier_1`, `doi_2`, `ark_1`, `uri_3`, `url_1` |
| `dcterms:relation*` | `relation_1`, `related_url_2`, `related_identifier_1` |

## Arbitrages

- Quand un nom ressemble fortement à un champ multilingue ou répété, le groupe de colonnes du template est préféré au champ exact.
  Exemple : `title_fr` doit suggérer `nakala:title_*`, pas `nakala:title`.
- Quand deux champs exacts concurrents existent, le champ le plus prioritaire dans le modèle NAKALA gagne.
  Exemple : `license` va préférer `nakala:license` à `dcterms:license` dans les overlays NAKALA.
- Le référentiel reste volontairement conservateur : on couvre des cas fréquents sans tenter une déduction sémantique trop large.

## Tests

- Les cas nominaux et les motifs sont couverts dans [tests/test_nakala_template_match_helpers.js](c:/Dev/Tablerreur/tests/test_nakala_template_match_helpers.js).
