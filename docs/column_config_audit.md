# Audit — Configuration par colonne dans le core

> **Date** : 2026-02-20
> **Périmètre** : `core/models.py`, `core/engine.py`, `core/rule_base.py`, `core/template.py`, `core/template_manager.py`, `core/rules/*.py`, `resources/templates/builtin/*.yml`
> **Nature** : lecture seule, aucune modification de code

---

## 1. Vue d'ensemble du pipeline de configuration

```
YAML template
    ↓ TemplateLoader.load()          deep_merge(base, overlay)
    ↓ TemplateLoader.expand_wildcards()   résolution des patterns glob
    ↓                                     priorité : '*' < column_groups < colonnes exactes
    ↓
config dict   {rules: {...}, columns: {col_name: {...}}}
    ↓
ValidationEngine.validate(df, columns, config)
    ↓ pour chaque règle × colonne :
    │   rule_cfg        = config["rules"][rule_id]          (paramètres globaux de la règle)
    │   col_cfg         = config["columns"][col_name]        (métadonnées de la colonne)
    │   rule_overrides  = col_cfg["rule_overrides"][rule_id] (surcharge règle × colonne)
    │   merged_cfg      = {**rule_cfg, **col_cfg (sans rule_overrides), **rule_overrides}
    ↓
rule.check(df, col, merged_cfg)
```

**Point clé** : `ColumnMeta` (dataclass définie dans `models.py`) n'est **jamais instanciée** dans le pipeline de validation. Le moteur passe directement les valeurs brutes du dict YAML aux règles. `ColumnMeta` sert de documentation de schéma et de type hint, mais n'est pas l'objet réel qui circule.

---

## 2. Options par colonne supportées par le moteur aujourd'hui

Ces options peuvent être posées dans `columns.<nom>` ou `column_groups.<pattern>` du YAML et atterrissent dans `merged_cfg` que reçoit chaque règle.

### 2a. Options lues et appliquées par au moins une règle

| Clé YAML | Type | Défaut YAML | Règle(s) qui la lisent | Effet |
|---|---|---|---|---|
| `unique` | bool | `false` | `generic.unique_column` | Active la règle si `true` ; ignorée sinon |
| `multiline_ok` | bool | `false` | `generic.unexpected_multiline` | Désactive la règle si `true` |
| `severity` | string | valeur de règle | toutes | Surcharge la sévérité de la règle pour cette colonne (via `rule_overrides`) |
| `enabled` | bool | `true` | moteur + toutes | Active/désactive la règle pour cette colonne (via `rule_overrides`) |
| `tokens` | liste | liste par défaut | `generic.pseudo_missing` | Jetons pseudo-vides à détecter |
| `regex` | string\|null | `null` | `nakala.created_format` uniquement | Surcharge le pattern de validation de date NAKALA par un regex personnalisé |

> **Note sur `tokens`** : paramètre global de règle, pas strictement par-colonne, mais peut être surchargé par `rule_overrides` pour une colonne donnée.

### 2b. Options présentes dans le YAML (et dans `ColumnMeta`) mais qu'aucune règle ne lit

Ces options traversent le moteur et arrivent dans `merged_cfg`, mais aucune règle ne les consulte.

| Clé YAML / `ColumnMeta` | Type | Déclarée dans ColumnMeta | Dans les YAML builtin | Règle qui l'exploite |
|---|---|---|---|---|
| `kind` | enum string | ✅ | ✅ (`free_text_short`, `free_text_long`, `controlled`, `structured`, `list`) | ❌ aucune |
| `required` | bool | ✅ | ✅ (`true`/`false`) | ❌ aucune |
| `allowed_values` | liste | ✅ | ❌ | ❌ aucune |
| `list_separator` | string | ✅ | ✅ (`\|`) | ❌ aucune (export seulement) |
| `violation_severity` | Severity | ✅ | ❌ | ❌ aucune |
| `nakala_field` | string\|null | ✅ | ❌ | ❌ aucune |

### 2c. Options présentes dans les YAML mais absentes de `ColumnMeta`

Ces clés sont lues dans le YAML et passées dans `merged_cfg`, mais elles ne correspondent à aucun champ de `ColumnMeta` et aucune règle ne les exploite non plus.

| Clé YAML | Où utilisée | Effet réel |
|---|---|---|
| `preset` | `nakala_extended.yml` (`uri`, `creator_name`) | Aucun — méta-documentation sans enforcement |
| `pipe_in_cell_warning` | `nakala_*.yml` | Aucun — intention non implémentée |
| `pipe_is_text` | `nakala_extended.yml` | Aucun — intention non implémentée |
| `required_columns` | niveau racine des overlays | Aucun — jamais lu par le moteur ni par une règle |
| `recommended_columns` | niveau racine de `nakala_extended.yml` | Aucun — jamais lu |

---

## 3. Paramètres par règle (référence complète)

### Règles d'hygiène — aucun paramètre colonne-spécifique

| Règle | Paramètres lus depuis `config` | Note |
|---|---|---|
| `generic.hygiene.leading_trailing_space` | `severity` | Aucun param colonne |
| `generic.hygiene.multiple_spaces` | `severity` | Aucun param colonne |
| `generic.hygiene.unicode_chars` | `severity` | Aucun param colonne |
| `generic.hygiene.invisible_chars` | `severity` | Aucun param colonne |

### Règles avec paramètres propres

| Règle | Paramètre | Défaut | Portée | Note |
|---|---|---|---|---|
| `generic.pseudo_missing` | `tokens` | 11 jetons | global/colonne | Liste configurable de pseudo-vides |
| `generic.unique_column` | `unique` | `false` | **colonne** | Règle dormante sauf si `unique: true` |
| `generic.unexpected_multiline` | `multiline_ok` | `false` | **colonne** | Règle muette si `multiline_ok: true` |
| `generic.soft_typing` | `min_count` | `30` | global | Nombre minimal de valeurs pour inférer |
| `generic.soft_typing` | `threshold` | `0.95` | global | ⚠️ Lu mais non transmis à `_dominant_type()` — **bug** (voir §5) |
| `generic.rare_values` | `max_distinct` | `50` | global | Seuil nb de valeurs distinctes |
| `generic.rare_values` | `max_ratio` | `0.2` | global | Seuil distinct/total |
| `generic.similar_values` | `threshold` | `90` | global | Score de similarité min (0-100) |
| `generic.similar_values` | `max_distinct` | `200` | global | Nb max de valeurs distinctes pour activer |
| `generic.duplicate_rows` | *(aucun)* | — | global | Règle globale (per_column=False) |
| `nakala.created_format` | `regex` | pattern W3C-DTF | **colonne** | Seule règle générique acceptant un regex par colonne |
| `nakala.deposit_type` | `_nakala_client` | `None` | injection | Muette sans client |
| `nakala.license` | `_nakala_client` | `None` | injection | Muette sans client |
| `nakala.language` | `_nakala_client` | `None` | injection | Muette sans client |

---

## 4. Ce qui manque — options utiles non implémentées

### 4.1 Vocabulaire contrôlé par colonne (`allowed_values`)

**État actuel** : `ColumnMeta.allowed_values: list[str]` est défini dans `models.py` mais aucune règle ne le lit. Aucun template YAML ne l'utilise.

**Besoin** : valider que chaque cellule d'une colonne appartient à une liste de valeurs autorisées (ex. : statuts, pays, types de documents).

**Ce qu'il faut** :
- **Nouvelle règle** `generic.allowed_values` (`per_column=True`)
  - Lit `config.get("allowed_values", [])` — si vide, ne fait rien
  - Signale chaque valeur hors vocabulaire
  - Fournit une suggestion via `rapidfuzz` si disponible
- **Paramètre YAML** : déjà prévu dans `ColumnMeta`, rien à ajouter au modèle

```yaml
# Exemple d'usage futur
columns:
  statut:
    kind: controlled
    allowed_values: [Publié, Brouillon, Archivé]
```

---

### 4.2 Type de contenu déclaré (`content_type` / `kind` enforcement)

**État actuel** : `kind: controlled | structured | free_text_short | free_text_long | list` est présent dans `ColumnMeta` et les YAML, mais n'est **jamais contrôlé**. `SoftTypingRule` infère statistiquement un type dominant, mais n'applique pas un type déclaré.

**Besoin** : déclarer explicitement `date`, `integer`, `float`, `email`, `url` par colonne et signaler toute valeur non conforme, même si la colonne n'est pas à 95 % homogène.

**Ce qu'il faut** :
- **Option A** — Nouveau paramètre `content_type` dans `ColumnMeta` + **nouvelle règle** `generic.content_type`
  - Valeurs possibles : `date`, `integer`, `float`, `email`, `url`
  - Règle stricte : chaque valeur non vide doit correspondre au type déclaré
  - Sévérité : ERROR par défaut
- **Option B** (moins invasive) — Étendre `SoftTypingRule` avec un paramètre `enforce_type` pour passer du mode inférence au mode assertion déclarée

Option A est préférable (séparation des responsabilités).

```yaml
# Exemple d'usage futur
columns:
  date_publication:
    kind: structured
    content_type: date
  nb_pages:
    kind: structured
    content_type: integer
```

---

### 4.3 Regex personnalisée par colonne (générique)

**État actuel** : `ColumnMeta.regex: str | None` est défini. `NakalaCreatedFormatRule` lit `config.get("regex")` mais c'est un comportement spécifique à NAKALA (surcharger son propre pattern W3C-DTF). Il n'existe pas de règle générique qui applique un regex arbitraire sur n'importe quelle colonne.

**Besoin** : par exemple, valider qu'une colonne `isbn` respecte `^\d{13}$`, ou qu'une colonne `doi` commence par `10.`.

**Ce qu'il faut** :
- **Nouvelle règle** `generic.regex` (`per_column=True`)
  - Lit `config.get("regex", None)` — si `None`, ne fait rien (règle dormante)
  - Compile le regex une seule fois par appel
  - Signale toute valeur non vide qui ne matche pas
  - Paramètre optionnel `regex_flags` (ex. `IGNORECASE`)
- `ColumnMeta.regex` est déjà prévu — aucun changement au modèle

```yaml
# Exemple d'usage futur
columns:
  isbn:
    kind: structured
    regex: '^\d{13}$'
  doi:
    kind: structured
    regex: '^10\.\d{4,}'
```

---

### 4.4 Longueur min/max par colonne

**État actuel** : aucun champ `min_length`/`max_length` dans `ColumnMeta`, aucun template YAML, aucune règle.

**Besoin** : signaler les cellules trop courtes (champ trop sommaire) ou trop longues (dépassement d'une contrainte métier).

**Ce qu'il faut** :
- **Modification de `ColumnMeta`** : ajouter `min_length: int | None = None` et `max_length: int | None = None`
- **Nouvelle règle** `generic.length` (`per_column=True`)
  - Lit `config.get("min_length", None)` et `config.get("max_length", None)`
  - Si les deux sont `None`, ne fait rien (règle dormante)
  - Sévérité : WARNING par défaut

```yaml
# Exemple d'usage futur
columns:
  titre:
    min_length: 3
    max_length: 250
  description:
    min_length: 10
```

---

### 4.5 Champ obligatoire non vide (`required`)

**État actuel** : `ColumnMeta.required: bool` est défini, les YAML builtin le renseignent (`id_*: required: true`), mais **aucune règle ne signale une cellule vide dans une colonne requise**.

**Besoin** : signaler toute cellule vide (NaN ou chaîne vide après strip) dans une colonne marquée `required: true`.

**Ce qu'il faut** :
- **Nouvelle règle** `generic.required` (`per_column=True`)
  - Lit `config.get("required", False)` — dormante si `false`
  - Sévérité : ERROR par défaut

---

### 4.6 Présence de colonnes requises dans le dataset

**État actuel** : `required_columns` est déclaré en racine des overlays NAKALA (ex. `nakala_baseline.yml`) mais le moteur ne lit jamais cette clé. Rien ne signale l'absence d'une colonne attendue.

**Besoin** : détecter que le fichier ne contient pas `nakala:type` alors que le template overlay l'exige.

**Ce qu'il faut** :
- **Mécanisme moteur** : dans `ValidationEngine.validate()`, avant de lancer les règles, vérifier `config.get("required_columns", [])` contre `df.columns` et émettre des `Issue` de type `generic.missing_column` (col=`"__schema__"`) pour chaque colonne absente
- **Ou nouvelle règle globale** `generic.missing_columns` (`per_column=False`) : moins invasif

---

## 5. Bug identifié : `SoftTypingRule.threshold` inutilisé

**Fichier** : `core/rules/soft_typing.py`

**Symptôme** : le template `generic_strict.yml` déclare `threshold: 0.90` pour `generic.soft_typing`, mais cela n'a aucun effet. La variable est lue à la ligne 55 (`threshold = float(config.get("threshold", 0.95))`) puis stockée en local… mais la fonction `_dominant_type(non_empty)` ligne 63 n'accepte pas `threshold` en paramètre et le hardcode à `0.95`.

```python
# soft_typing.py l.55 : lu mais jamais utilisé
threshold = float(config.get("threshold", 0.95))
# ...
# l.63 : appel sans threshold → toujours 0.95
dom_type = _dominant_type(non_empty)
```

**Correction nécessaire** (hors périmètre de cet audit) : passer `threshold` à `_dominant_type()`.

---

## 6. Tableau de synthèse

| Option | Dans `ColumnMeta` | Dans les YAML | Appliquée par une règle | Manque / Action requise |
|---|---|---|---|---|
| `unique` | ✅ | ✅ | ✅ `generic.unique_column` | — |
| `multiline_ok` | ✅ | ✅ | ✅ `generic.unexpected_multiline` | — |
| `kind` | ✅ | ✅ | ❌ | Nouvelle règle ou enforcement moteur |
| `required` | ✅ | ✅ | ❌ | Nouvelle règle `generic.required` |
| `allowed_values` | ✅ | ❌ | ❌ | Nouvelle règle `generic.allowed_values` |
| `regex` | ✅ | ❌ (generic) | ⚠️ NAKALA seulement | Nouvelle règle générique `generic.regex` |
| `list_separator` | ✅ | ✅ | ❌ | Export only — OK |
| `violation_severity` | ✅ | ❌ | ❌ | Doublon avec `severity` — à clarifier |
| `nakala_field` | ✅ | ❌ | ❌ | Inutilisé — à documenter ou supprimer |
| `content_type` | ❌ | ❌ | ❌ | Nouveau champ `ColumnMeta` + nouvelle règle |
| `min_length` | ❌ | ❌ | ❌ | Nouveau champ `ColumnMeta` + nouvelle règle |
| `max_length` | ❌ | ❌ | ❌ | Nouveau champ `ColumnMeta` + nouvelle règle |
| `preset` | ❌ | ✅ | ❌ | Non défini — à implémenter ou documenter |
| `pipe_in_cell_warning` | ❌ | ✅ | ❌ | Non défini — intention non implémentée |
| `required_columns` (racine) | — | ✅ | ❌ | Mécanisme moteur ou règle globale |
| `threshold` (soft_typing) | — | ✅ | ⚠️ bug | Correction `_dominant_type()` |

---

## 7. Priorisation des travaux

| Priorité | Manque | Nature | Complexité |
|---|---|---|---|
| 🔴 Haute | `required` non enforced | Nouvelle règle `generic.required` | Faible |
| 🔴 Haute | `allowed_values` non enforced | Nouvelle règle `generic.allowed_values` | Faible |
| 🔴 Haute | `threshold` SoftTypingRule inutilisé | Fix paramètre `_dominant_type()` | Très faible |
| 🟠 Moyenne | Regex générique par colonne | Nouvelle règle `generic.regex` | Faible |
| 🟠 Moyenne | `required_columns` non vérifié | Règle globale ou moteur | Moyenne |
| 🟡 Basse | Longueur min/max | Nouveau champ ColumnMeta + règle `generic.length` | Moyenne |
| 🟡 Basse | `content_type` déclaré | Nouveau champ ColumnMeta + règle `generic.content_type` | Élevée |
| 🟡 Basse | `preset` (uri, creator_name) | Définir le mécanisme ou supprimer | À clarifier |
| ⚪ Info | `violation_severity` vs `severity` | Doublon à documenter ou consolider | Très faible |
