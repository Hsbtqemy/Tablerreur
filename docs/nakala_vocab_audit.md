# Audit : Intégration vocabulaires NAKALA dans Tablerreur

> Audit réalisé le 2026-02-21. Ne modifie aucun code — document de référence pour l'implémentation.

---

## 1. État du client `nakala_api.py`

### 1.1 Ce qui existe

`NakalaClient` (classe unique, `core/nakala_api.py`) :

| Méthode | Rôle |
|---|---|
| `__init__(cache_path, timeout)` | Charge le cache disque (`nakala_cache.json`) |
| `_fetch_sync(endpoint)` | Appel HTTP synchrone, mise en cache thread-safe |
| `fetch_deposit_types()` | Retourne la liste des types de dépôt |
| `fetch_licenses()` | Retourne la liste des licences |
| `fetch_languages()` | Retourne la liste des codes langue |
| `fetch_all_async(on_done)` | Lance les 3 fetches en thread daemon |
| `is_valid_deposit_type(v)` | Retourne True si vide ou v ∈ vocab (fail-open) |
| `is_valid_license(v)` | Idem |
| `is_valid_language(v)` | Idem |

La logique de cache disque et le fail-open (retourne True si le vocab est vide) sont **corrects**.
`httpx` est importé de manière optionnelle avec fallback à `[]` — bon design.

### 1.2 Bugs critiques découverts

**Bug 1 — Mauvais endpoint pour les types de dépôt**

```python
# nakala_api.py ligne 34 — FAUX
"deposit_types": "/vocabularies/deposittypes",

# Endpoint réel (vérifié)
"deposit_types": "/vocabularies/datatypes",
```

`/vocabularies/deposittypes` retourne `404`. L'endpoint correct est `/vocabularies/datatypes`.

**Bug 2 — Mauvais parsing pour les types de dépôt**

L'endpoint `/vocabularies/datatypes` retourne un **tableau plat de chaînes** (URIs COAR), pas des objets :

```json
["http://purl.org/coar/resource_type/c_c513", "http://purl.org/coar/resource_type/c_2f33", ...]
```

Le code actuel fait `item.get("id")` sur chaque élément en supposant un dict → retourne toujours `None` → liste vide. **La règle `nakala.deposit_type` ne valide jamais rien**, même avec réseau.

**Bug 3 — Mauvais parsing pour les licences**

L'endpoint `/vocabularies/licenses` retourne des objets `{"code": "CC-BY-4.0", "name": "..."}`.

```python
# nakala_api.py ligne 93 — cherche "id" ou "@id", jamais présents
return [item.get("id") or item.get("@id", "") for item in data ...]
```

Les clés réelles sont `"code"` et `"name"`. Le parser retourne `""` pour chaque licence → liste de chaînes vides. **La règle `nakala.license` ne valide jamais rien non plus.**

**Bug 4 — Parsing langues : correct par accident**

L'endpoint `/vocabularies/languages` retourne `{"id": "fra", "label": "..."}`. Le code fait `item.get("id") or item.get("code", "")` → `"id"` est bien présent → **fonctionne**, mais `item.get("code", "")` est inutile et trompeur.

### 1.3 Bug d'intégration : client jamais injecté dans le web

`NakalaClient` est conçu pour être injecté via `compile_config(nakala_client=...)`. Or dans `web/app.py`, l'endpoint `POST /api/jobs/{id}/validate` appelle :

```python
config = mgr.compile_config(
    generic_id=job.template_id,
    overlay_id=job.overlay_id,
    column_names=list(df.columns),
    # nakala_client=??? → ABSENT
)
```

**Conséquence** : dans l'UI web, les trois règles `nakala.deposit_type`, `nakala.license`, `nakala.language` reçoivent `config.get("_nakala_client") is None` et **retournent toujours `[]`**. Les templates NAKALA ne valident pas les vocabulaires contrôlés en mode web. Seule `nakala.created_format` fonctionne (regex pure).

### 1.4 Tests existants

- `tests/test_template.py` : teste le chargement et la fusion des templates NAKALA. ✅
- `tests/test_rules.py` : **zéro test** pour les 4 règles `nakala.*`. ❌
- Aucun test pour `NakalaClient` lui-même. ❌

### 1.5 Verdict

| Composant | État |
|---|---|
| Architecture (cache, fail-open, injection) | ✅ Bonne |
| Endpoint types de dépôt | ❌ 404 — à corriger |
| Parsing types de dépôt | ❌ Bug — liste plate non gérée |
| Parsing licences | ❌ Bug — clé `"code"` ignorée |
| Parsing langues | ⚠️ Fonctionne par coïncidence |
| Intégration web | ❌ Client jamais instancié dans `web/app.py` |
| Tests des règles NAKALA | ❌ Absents |

---

## 2. Vocabulaires NAKALA disponibles via API

Tous les endpoints sont sur `https://api.nakala.fr`.

| Vocabulaire | Endpoint réel | Nb valeurs | Format de réponse |
|---|---|---|---|
| Types de ressource | `GET /vocabularies/datatypes` | 29 | Tableau plat de chaînes (URIs COAR) |
| Licences | `GET /vocabularies/licenses` | 620 | `[{"code": "CC-BY-4.0", "name": "..."}]` |
| Langues | `GET /vocabularies/languages?limit=10000` | 8039 | `[{"id": "fra", "label": "..."}]` |

### 2.1 Types de ressource COAR (29 valeurs)

Ce sont des **URIs complètes**, pas des codes courts :

```
http://purl.org/coar/resource_type/c_c513   (image)
http://purl.org/coar/resource_type/c_2f33   (journal article)
http://purl.org/coar/resource_type/c_ddb1   (dataset)
http://purl.org/coar/resource_type/c_5ce6   (software)
http://purl.org/coar/resource_type/c_12cd   (doctoral thesis)
http://purl.org/coar/resource_type/c_46ec   (preprint)
http://purl.org/coar/resource_type/c_7ad9   (working paper)
http://purl.org/coar/resource_type/c_beb9   (report)
http://purl.org/coar/resource_type/c_816b   (conference paper)
... (20 autres)
```

> **Implication** : la valeur à valider dans `nakala:type` est une URI COAR complète, pas un libellé humain. Les templates et l'UI doivent en tenir compte.

### 2.2 Licences (620 codes SPDX)

Les valeurs valides sont les **codes SPDX** (`"code"`), ex. : `CC-BY-4.0`, `CC0-1.0`, `MIT`, `Apache-2.0`, `GPL-2.0-only`…

Licences les plus courantes en SHS :
- `CC-BY-4.0` — Creative Commons Attribution 4.0
- `CC-BY-SA-4.0` — CC Attribution-ShareAlike 4.0
- `CC-BY-NC-4.0` — CC Attribution-NonCommercial 4.0
- `CC0-1.0` — Domaine public (CC Zero)
- `Etalab-2.0` — Licence Ouverte Etalab
- `ODbL-1.0` — Open Database License

### 2.3 Langues (8039 codes ISO 639-3)

Les valeurs valides sont des **codes ISO 639-3** à 3 lettres (`"id"`), ex. : `fra`, `eng`, `deu`, `spa`, `ita`, `por`…

> Attention : ISO 639-3 (3 lettres, `fra`) ≠ ISO 639-1 (2 lettres, `fr`). L'UI web actuelle propose un preset "Langue ISO 639" avec regex `^[a-z]{2,3}$` qui accepte les deux formats. NAKALA attend le format **3 lettres uniquement**.

---

## 3. Mapping colonne NAKALA → vocabulaire → valeurs attendues

### 3.1 Champs obligatoires

| Colonne | Vocabulaire | Valeurs attendues | Règle actuelle | État |
|---|---|---|---|---|
| `nakala:type` | COAR via `/vocabularies/datatypes` | 29 URIs complètes | `nakala.deposit_type` | ❌ Ne fire pas (bugs 1+2) |
| `nakala:title` | Texte libre | Non vide | `generic.required` + `generic.pseudo_missing` | ✅ Fonctionne |
| `nakala:creator` | Format structuré | `"Nom, Prénom"` ou `"Nom, Prénom [ORCID]"` | Aucune règle de format | ❌ Manquant |
| `nakala:created` | W3C-DTF | `YYYY`, `YYYY-MM`, `YYYY-MM-DD` | `nakala.created_format` (regex) | ✅ Fonctionne |
| `nakala:license` | SPDX via `/vocabularies/licenses` | 620 codes (`"CC-BY-4.0"`…) | `nakala.license` | ❌ Ne fire pas (bug 3) |

### 3.2 Champs recommandés

| Colonne | Vocabulaire | Valeurs attendues | Règle actuelle | État |
|---|---|---|---|---|
| `dcterms:language` | ISO 639-3 via `/vocabularies/languages` | Codes 3 lettres (`fra`, `eng`…) | `nakala.language` | ⚠️ Ne fire pas (client absent) |
| `dcterms:description` | Texte libre | Multiligne OK, `\|` autorisé | `multiline_ok: true` | ✅ Configuré |
| `dcterms:subject` | Texte libre (mots-clés) | Liste avec `\|` | `list_separator: "\|"` | ✅ Configuré |
| `dcterms:identifier` | URI | `https?://…` ou `ark:/…` | `preset: uri` (non implémenté) | ❌ Preset `uri` inexistant |
| `dcterms:relation` | URI | idem | `preset: uri` | ❌ Idem |

---

## 4. Ce qui existe vs ce qu'il faut ajouter

### 4.1 Ce qui existe déjà et fonctionne

| Composant | Fichier | État |
|---|---|---|
| Architecture d'injection du client | `template_manager.py:237` | ✅ |
| Règle `nakala.created_format` | `nakala_rules.py` | ✅ Regex, offline |
| Templates YAML (baseline + extended) | `builtin/nakala_baseline.yml`, `nakala_extended.yml` | ✅ Structure OK |
| Fusion templates via `TemplateManager` | `template_manager.py` | ✅ |
| Tests de chargement des templates | `tests/test_template.py` | ✅ |
| Cache disque JSON pour vocabulaires | `nakala_api.py` | ✅ Architecture OK |
| Fail-open si réseau indisponible | `nakala_rules.py` | ✅ |

### 4.2 Ce qui est cassé et doit être corrigé

| Problème | Fichier | Priorité |
|---|---|---|
| Endpoint `/vocabularies/deposittypes` → 404 | `nakala_api.py:34` | 🔴 Critique |
| Parsing types : liste de strings, pas de dicts | `nakala_api.py:89` | 🔴 Critique |
| Parsing licences : clé `"code"` ignorée | `nakala_api.py:93` | 🔴 Critique |
| Client NAKALA jamais injecté dans `web/app.py` | `web/app.py:548` | 🔴 Critique |

### 4.3 Ce qui manque et doit être ajouté

| Fonctionnalité | Priorité | Effort |
|---|---|---|
| Endpoint web `GET /api/vocabularies/nakala/{type}` | 🔴 Haute | Faible |
| Instanciation + injection du `NakalaClient` dans `validate_job` | 🔴 Haute | Faible |
| Tests des règles `nakala.*` | 🟡 Moyenne | Moyen |
| `allowed_values` offline pré-remplis dans templates (fallback) | 🟡 Moyenne | Moyen |
| Validation format `nakala:creator` (`^.+, .+$`) | 🟡 Moyenne | Faible |
| Règle `preset: uri` pour `dcterms:identifier` / `dcterms:relation` | 🟡 Moyenne | Faible |
| Sélecteur de vocabulaire NAKALA dans l'UI web | 🟡 Moyenne | Moyen |
| Preset ISO 639-3 (3 lettres strictes, pas 2-3) | 🟡 Moyenne | Faible |
| Suggestions de correction depuis le vocabulaire (top-N similaires) | 🟠 Basse | Élevé |
| TTL sur le cache nakala (re-fetch auto toutes les 24h) | 🟠 Basse | Faible |
| Endpoint `GET /api/vocabularies/nakala/coar-labels` (URI→libellé FR) | 🟠 Basse | Moyen |

---

## 5. Plan d'implémentation recommandé

### Phase 1 — Corriger les bugs (prerequis, ~1h)

> Sans cette phase, les règles NAKALA sont inopérantes.

**1a.** Corriger `nakala_api.py` :
- `_ENDPOINTS["deposit_types"]` → `/vocabularies/datatypes`
- `fetch_deposit_types()` : données = liste plate de strings → retourner directement `[item for item in data if isinstance(item, str)]`
- `fetch_licenses()` : données = `[{"code": "...", "name": "..."}]` → `[item["code"] for item in data if "code" in item]`
- `fetch_languages()` : données = `[{"id": "...", "label": "..."}]` → `[item["id"] for item in data if "id" in item]` (déjà presque bon, nettoyer)

**1b.** Ajouter un singleton `NakalaClient` dans `web/app.py` :
```python
# À ajouter une fois au niveau module dans web/app.py
from spreadsheet_qa.core.nakala_api import NakalaClient
_nakala_client = NakalaClient(cache_path=Path(tempfile.gettempdir()) / "nakala_cache.json")
_nakala_client.fetch_all_async()  # prefetch en arrière-plan au démarrage
```
Et passer `nakala_client=_nakala_client` dans `mgr.compile_config(...)` dans `validate_job`.

**1c.** Ajouter des tests unitaires pour les 4 règles NAKALA (avec mock du client).

---

### Phase 2 — Endpoint web vocabulaires (~30 min)

Ajouter dans `web/app.py` :

```
GET /api/vocabularies/nakala/deposit-types   → liste des 29 URIs COAR + libellés
GET /api/vocabularies/nakala/licenses        → liste des 620 codes SPDX
GET /api/vocabularies/nakala/languages       → liste des codes ISO 639-3
```

Ces endpoints servent l'UI web pour peupler les dropdowns de configuration de colonne (champ `allowed_values`).

---

### Phase 3 — UI web : sélecteur de vocabulaire (~2h)

Dans le panneau de configuration par colonne (étape 2 de l'UI) :
- Si le template est NAKALA (overlay `nakala_baseline` ou `nakala_extended`) et que la colonne est `nakala:type`, `nakala:license`, `dcterms:language` : afficher un bouton "Charger le vocabulaire NAKALA"
- Au clic : appel `GET /api/vocabularies/nakala/...` → peupler `allowed_values` de la colonne automatiquement
- Afficher les valeurs avec libellés lisibles (ex. `"CC-BY-4.0"` → `"Creative Commons Attribution 4.0"`)

---

### Phase 4 — Templates : allowed_values offline (optionnel, ~1h)

Pré-remplir les templates YAML avec les valeurs actuelles comme fallback hors-ligne :

```yaml
# nakala_baseline.yml
columns:
  "nakala:license":
    allowed_values:
      - "CC-BY-4.0"
      - "CC-BY-SA-4.0"
      - "CC-BY-NC-4.0"
      - "CC0-1.0"
      - "Etalab-2.0"
      # ... (subset des plus utilisées en SHS)
    allowed_values_locked: true  # verrouillé — ne pas modifier depuis l'UI
```

Avantage : la règle `generic.allowed_values` fonctionnerait même sans réseau ni client injecté.

---

### Phase 5 — Améliorations (futures)

- **Suggestions de correction** : quand une valeur est invalide, trouver les N valeurs COAR/SPDX les plus proches via `rapidfuzz` (déjà présent dans les dépendances)
- **Libellés COAR en français** : les URIs COAR ont des libellés (`c_ddb1` = « jeu de données »). Stocker le mapping URI → libellé FR pour l'affichage UI
- **TTL cache** : ajouter un champ `_fetched_at` dans `nakala_cache.json` et re-fetcher si > 24h
- **Format `nakala:creator`** : ajouter une règle regex `^[^,]+, [^,]+` pour valider le format `Nom, Prénom`
- **Preset ISO 639-3 strict** : ajuster le preset "Langue ISO 639" de l'UI pour accepter exactement 3 lettres (`^[a-z]{3}$`), pas 2-3

---

## Résumé exécutif

```
État actuel
───────────
✅ nakala.created_format  → fonctionne (regex offline)
❌ nakala.deposit_type    → dead code (endpoint 404 + parsing cassé + client absent)
❌ nakala.license         → dead code (parsing cassé + client absent)
❌ nakala.language        → dead code (client absent)

Minimum viable (Phase 1) : ~1-2h de corrections ciblées
  → 3 bugs dans nakala_api.py (10 lignes)
  → 1 injection dans web/app.py (5 lignes)
  → tests nakala_rules (nouveau fichier)

Après Phase 1, toutes les règles NAKALA fonctionneront dans l'UI web.
```
