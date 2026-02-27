# Overlay NAKALA

## Vue d'ensemble

L'overlay NAKALA ajoute des règles de validation spécifiques aux jeux de données destinés au dépôt sur [NAKALA](https://nakala.fr), la plateforme de données de recherche de Huma-Num.

Deux overlays sont disponibles, à appliquer par-dessus le template générique via `TemplateManager` :
- **NAKALA — Référence** (`nakala_baseline`) — valide les 5 champs obligatoires uniquement.
- **NAKALA — Étendu** (`nakala_extended`) — valide les 5 champs obligatoires + 20 champs recommandés `dcterms:*`.

Activation dans l'UI : **Modèles… → Appliquer un modèle → Overlay → NAKALA — Référence** ou **NAKALA — Étendu**.

**Référence complète (formats de validation) :** voir [docs/nakala-validation-formats.md](nakala-validation-formats.md) — W3C-DTF, LCSH, Box, Point, RelationType, endpoints API, etc.

---

## Champs obligatoires (nakala:\*)

Ces 5 champs sont requis dans les deux overlays.

| Champ | Kind | Règle principale | Notes |
|-------|------|-----------------|-------|
| `nakala:type` | controlled | `nakala.deposit_type` | 29 URIs COAR ; repli statique si hors-ligne |
| `nakala:title` | free_text_short | `generic.required` | Valeurs pseudo-manquantes → ERROR |
| `nakala:creator` | structured | `generic.regex` | Format `Nom, Prénom` ; `Anonyme` accepté ; `|` pour multi-auteurs |
| `nakala:created` | structured | `nakala.created_format` | W3C-DTF : `AAAA`, `AAAA-MM`, `AAAA-MM-JJ` ; `Inconnue` accepté |
| `nakala:license` | controlled | `nakala.license` | Codes SPDX (ex. `CC-BY-4.0`) ; validation dynamique via API |

---

## Champs recommandés — équivalents dcterms:\* des obligatoires

Présents dans les deux overlays (optionnels, validés si la colonne existe dans le CSV).

| Champ | Kind | Règle | Notes |
|-------|------|-------|-------|
| `dcterms:type` | controlled | `nakala.deposit_type` | Mêmes 29 URIs COAR que `nakala:type` |
| `dcterms:title` | free_text_short | — | Équivalent dcterms |
| `dcterms:creator` | structured | `generic.regex` | Format `Nom, Prénom` ; `Anonyme` accepté |
| `dcterms:created` | structured | `nakala.created_format` | Même format W3C-DTF |
| `dcterms:license` | controlled | `nakala.license` | Même vocabulaire SPDX |

---

## Champs recommandés supplémentaires (nakala_extended uniquement)

| Champ | Kind | Validation | Notes |
|-------|------|-----------|-------|
| `dcterms:description` | free_text_long | — | Multilignes OK ; `|` autorisé comme texte |
| `dcterms:language` | controlled | `nakala.language` | Code ISO 639-3 (ex. `fra`, `eng`, `deu`) ; `|` pour multi-langues |
| `dcterms:subject` | list | — | Mots-clés ; séparateur `|` ; suggère colonnes répétées |
| `dcterms:publisher` | free_text_short | — | Éditeur (texte libre) |
| `dcterms:contributor` | structured | `generic.regex` | Format `Nom, Prénom` ; `Anonyme` accepté |
| `dcterms:rights` | free_text_short | — | Mention de droits (texte libre) |
| `dcterms:rightsHolder` | free_text_short | — | Titulaire des droits |
| `dcterms:relation` | free_text_short | — | URI ou texte libre |
| `dcterms:source` | free_text_short | — | URI ou texte libre |
| `dcterms:spatial` | free_text_short | — | Couverture spatiale (texte libre, `dcterms:Point/Box`) |
| `dcterms:available` | structured | `generic.regex` | Format W3C-DTF : `^\\d{4}(-\\d{2}(-\\d{2})?)?$` |
| `dcterms:modified` | structured | `generic.regex` | Format W3C-DTF |
| `dcterms:format` | structured | `generic.regex` | Type MIME : `^[a-z]+/[a-z0-9\\.\\-\\+]+$` (ex. `application/pdf`) |
| `dcterms:abstract` | free_text_long | — | Résumé long ; multilignes OK ; `|` autorisé comme texte |
| `dcterms:mediator` | free_text_short | — | Entité médiatisant l'accès (ex. enseignant) |

---

## Règles NAKALA (`nakala_rules.py`)

| rule_id | Colonne(s) cible | Description |
|---------|-----------------|-------------|
| `nakala.deposit_type` | `nakala:type`, `dcterms:type` | Vérifie que la valeur est une URI COAR valide. Si libellé reconnu (ex. `article`), suggère l'URI COAR. |
| `nakala.license` | `nakala:license`, `dcterms:license` | Vérifie que la valeur est un code SPDX valide (via API ou fallback vide hors-ligne). |
| `nakala.created_format` | `nakala:created`, `dcterms:created` | Vérifie le format W3C-DTF. Activé globalement, désactivé par `rule_overrides` sur les colonnes non-date. |
| `nakala.language` | `dcterms:language` | Vérifie que la valeur est un code ISO 639-3 valide (via API). |

### Comportement de `nakala.created_format`

La règle `nakala.created_format` est **activée globalement** dans les templates mais **désactivée par `rule_overrides`** sur toutes les colonnes non-date. Seules `nakala:created` et `dcterms:created` la conservent active :

```yaml
# Colonne date : règle activée explicitement
"nakala:created":
  rule_overrides:
    nakala.created_format:
      enabled: true

# Toutes les autres colonnes : règle désactivée
"nakala:title":
  rule_overrides:
    nakala.created_format:
      enabled: false
```

Cela est nécessaire car le moteur de validation n'autorise pas la ré-activation par colonne d'une règle globalement désactivée.

---

## Mapping COAR libellé → URI (`core/coar_mapping.py`)

Le module `coar_mapping.py` fournit un dictionnaire bilingue (FR/EN) libellé → URI COAR pour les 29 types de ressource NAKALA.

```python
from spreadsheet_qa.core.coar_mapping import (
    label_to_coar_uri,    # "article" → "http://purl.org/coar/resource_type/c_6501"
    coar_uri_to_label,    # URI → libellé FR
    suggest_coar_uri,     # correspondance approchée (exact puis inclusion)
    COAR_URI_TO_LABEL_FR, # dict URI → libellé FR
    COAR_LABEL_TO_URI,    # dict libellé (minuscules) → URI
)
```

Quand `nakala.deposit_type` reçoit une valeur non-URI mais reconnue comme libellé (ex. `article`, `Jeu de données`, `dataset`), elle génère une issue avec le message « Type reconnu — utilisez l'URI COAR : … » et une **suggestion automatique**.

### Exemples de correspondances

| Valeur saisie | URI suggérée |
|---------------|-------------|
| `article` / `Article de journal` | `http://purl.org/coar/resource_type/c_6501` |
| `jeu de données` / `dataset` | `http://purl.org/coar/resource_type/c_ddb1` |
| `logiciel` / `software` | `http://purl.org/coar/resource_type/c_5ce6` |
| `rapport` / `report` | `http://purl.org/coar/resource_type/c_93fc` |
| `vidéo` / `video` | `http://purl.org/coar/resource_type/c_12ce` |

---

## Sources de vocabulaires API NAKALA

Les vocabulaires sont récupérés via l'API NAKALA et mis en cache dans `nakala_cache.json`.

| Vocabulaire | Endpoint | Utilisation dans Tablerreur |
|-------------|----------|-----------------------------|
| Types de ressource (COAR) | `https://api.nakala.fr/vocabularies/datatypes` | `nakala.deposit_type` ; labels FR via `coar_mapping.py` |
| Licences (SPDX) | `https://api.nakala.fr/vocabularies/licenses` | `nakala.license` (620 codes) |
| Langues (ISO 639-3) | `https://api.nakala.fr/vocabularies/languages?limit=10000` | `nakala.language` (8 039 codes) |

Si hors-ligne : les règles basées sur l'API (`nakala.deposit_type`, `nakala.license`, `nakala.language`) passent silencieusement. `nakala.created_format` est purement regex et fonctionne sans connexion.

---

## Politique séparateur `|`

- `|` est le séparateur multi-valeur en cellule pour les champs répétables.
- Pour `dcterms:description` et `dcterms:abstract` : `|` est autorisé comme contenu textuel (`pipe_is_text: true`).
- Pour `nakala:creator`, `dcterms:subject` : `|` en cellule déclenche un **WARNING** suggérant de scinder en colonnes répétées (`creator_1`, `creator_2`, …).
- Export NAKALA : `multivalues_mode: expanded` par défaut (colonnes `creator_1`, `creator_2`, …).

---

## Comparaison Baseline vs Extended

| Fonctionnalité | NAKALA — Référence | NAKALA — Étendu |
|----------------|-------------------|-----------------|
| 5 champs obligatoires `nakala:*` | ✅ | ✅ |
| Règle `nakala.deposit_type` | ✅ | ✅ |
| Règle `nakala.license` | ✅ | ✅ |
| Règle `nakala.created_format` | ✅ | ✅ |
| Règle `nakala.language` | — | ✅ |
| Équivalents `dcterms:*` des obligatoires | ✅ | ✅ |
| 15 champs recommandés supplémentaires `dcterms:*` | — | ✅ |
| Groupes de colonnes multilingues (`title_*`, `description_*`) | — | ✅ |
| Colonnes mots-clés (`keywords_*`) | — | ✅ |
| Colonnes identifiant/relation (regex URI) | — | ✅ |

---

## Exemple `rule_overrides` dans un template YAML

```yaml
columns:
  "nakala:title":
    kind: free_text_short
    required: true
    rule_overrides:
      generic.pseudo_missing:
        enabled: true
        severity: ERROR    # escalade de WARNING → ERROR pour cette colonne
      nakala.created_format:
        enabled: false     # désactivé car ce n'est pas une colonne date
```

Le bloc `rule_overrides` est par colonne et par règle. Il ne s'applique pas aux autres colonnes. Le moteur applique : `config_règle_globale < métadonnées_colonne < rule_override`.

---

## Mapping colonnes CSV → URI NAKALA (export)

Les templates utilisent des noms courts (`nakala:creator`, `dcterms:description`). Voici la correspondance avec les URIs complètes utilisées dans l'API NAKALA :

| Colonne template | URI NAKALA / Dublin Core |
|-----------------|--------------------------|
| `nakala:type` | `http://nakala.fr/terms#type` |
| `nakala:title` | `http://nakala.fr/terms#title` |
| `nakala:creator` | `http://nakala.fr/terms#creator` |
| `nakala:created` | `http://nakala.fr/terms#created` |
| `nakala:license` | `http://nakala.fr/terms#license` |
| `dcterms:type` | `http://purl.org/dc/terms/type` |
| `dcterms:title` | `http://purl.org/dc/terms/title` |
| `dcterms:creator` | `http://purl.org/dc/terms/creator` |
| `dcterms:created` | `http://purl.org/dc/terms/created` |
| `dcterms:license` | `http://purl.org/dc/terms/license` |
| `dcterms:description` | `http://purl.org/dc/terms/description` |
| `dcterms:language` | `http://purl.org/dc/terms/language` |
| `dcterms:subject` | `http://purl.org/dc/terms/subject` |
| `dcterms:publisher` | `http://purl.org/dc/terms/publisher` |
| `dcterms:contributor` | `http://purl.org/dc/terms/contributor` |
| `dcterms:rights` | `http://purl.org/dc/terms/rights` |
| `dcterms:rightsHolder` | `http://purl.org/dc/terms/rightsHolder` |
| `dcterms:relation` | `http://purl.org/dc/terms/relation` |
| `dcterms:source` | `http://purl.org/dc/terms/source` |
| `dcterms:spatial` | `http://purl.org/dc/terms/spatial` |
| `dcterms:available` | `http://purl.org/dc/terms/available` |
| `dcterms:modified` | `http://purl.org/dc/terms/modified` |
| `dcterms:format` | `http://purl.org/dc/terms/format` |
| `dcterms:abstract` | `http://purl.org/dc/terms/abstract` |
| `dcterms:mediator` | `http://purl.org/dc/terms/mediator` |
