# CLAUDE.md — Tablerreur

> Ce fichier est lu automatiquement par Claude Code. Il décrit le projet, son état actuel et la migration en cours.

---

## Identité du projet

**Tablerreur** (paquet Python : `spreadsheet_qa`) — vérificateur de tableurs (CSV/XLSX) pour non-techniciens.
Fonctions : charger → valider (règles configurables) → corriger → exporter.
Langue de l'UI et des exports : **français exclusivement**. Tout texte visible par l'utilisateur final doit être en français.

---

## Architecture actuelle

```
Tablerreur/
├── src/spreadsheet_qa/
│   ├── __main__.py          # Entry point (python -m spreadsheet_qa → lance Qt legacy)
│   ├── core/                # Métier pur (AUCUNE dépendance Qt/UI/web)
│   │   ├── models.py        # Issue, Patch, DatasetMeta, Severity, IssueStatus…
│   │   ├── engine.py        # ValidationEngine
│   │   ├── rule_base.py     # Rule ABC + RuleRegistry singleton
│   │   ├── rules/           # Règles concrètes
│   │   │   ├── hygiene.py         # generic.hygiene.* (4 règles)
│   │   │   ├── duplicates.py      # generic.duplicate_rows, generic.unique_column
│   │   │   ├── soft_typing.py     # generic.soft_typing
│   │   │   ├── multiline.py       # generic.unexpected_multiline
│   │   │   ├── pseudo_missing.py  # generic.pseudo_missing
│   │   │   ├── allowed_values.py  # generic.allowed_values (+ mode liste)
│   │   │   ├── regex_rule.py      # generic.regex
│   │   │   ├── length.py          # generic.length
│   │   │   ├── content_type.py    # generic.content_type
│   │   │   ├── required.py        # generic.required
│   │   │   ├── forbidden_chars.py # generic.forbidden_chars
│   │   │   ├── case_rule.py       # generic.case
│   │   │   ├── list_items.py      # generic.list_items
│   │   │   ├── rare_values.py     # generic.rare_values
│   │   │   ├── similar_values.py  # generic.similar_values
│   │   │   └── nakala_rules.py    # nakala.* (4 règles NAKALA)
│   │   ├── issue_store.py   # Stockage issues en mémoire
│   │   ├── dataset.py       # DatasetLoader (CSV/XLSX, encodage, délimiteur)
│   │   ├── template.py      # TemplateLoader (YAML, deep_merge, wildcards)
│   │   ├── template_manager.py  # Découverte templates (builtin/user/project)
│   │   ├── project.py       # ProjectManager + NullProjectManager
│   │   ├── patch.py         # PatchWriter + NullPatchWriter
│   │   ├── commands.py      # Command ABC, ApplyCellFixCommand, BulkCellFixCommand…
│   │   ├── history.py       # CommandHistory (undo/redo, max 500)
│   │   ├── exporters.py     # XLSX, CSV (;), TXT rapport, issues.csv
│   │   ├── text_utils.py    # INVISIBLE_RE, UNICODE_SUSPECTS
│   │   └── nakala_api.py    # Client vocabulaires NAKALA
│   ├── ui/                  # PySide6 — ABANDONNÉ (ne pas y toucher)
│   │   ├── app.py           # create_app(), stylesheet
│   │   ├── signals.py       # AppSignals singleton
│   │   ├── main_window.py   # MainWindow
│   │   ├── i18n.py          # t(key), glossaire FR
│   │   ├── controllers/     # Load, Validation, Fix, Export, Project
│   │   ├── dialogs/         # Load, Export, TemplateLibrary, TemplateEditor
│   │   ├── panels/          # IssuesPanel, FindFixDrawer
│   │   └── table/           # SpreadsheetTableModel, SpreadsheetTableView
│   ├── web/                 # FastAPI — frontend actif (Tauri + online)
│   │   ├── __main__.py      # python -m spreadsheet_qa.web (launcher standalone)
│   │   ├── app.py           # API FastAPI + tous les endpoints
│   │   ├── jobs.py          # Jobs temporaires (TTL 1h)
│   │   ├── launcher.py      # Port auto, démarrage serveur, ouverture navigateur
│   │   └── static/
│   │       ├── index.html   # UI HTML 5 étapes
│   │       ├── app.js       # Logique frontend (vanilla JS)
│   │       ├── style.css    # Styles (CSS pur, variables cohérentes)
│   │       └── fr.json      # Chaînes FR (réservé pour i18n future)
│   └── resources/templates/ # YAML builtin (generic_default, generic_strict, nakala_*)
├── src-tauri/               # App desktop Tauri v2
│   ├── Cargo.toml           # Dépendances Rust (tauri, tauri-plugin-shell, …)
│   ├── Cargo.lock
│   ├── build.rs
│   ├── tauri.conf.json      # Config Tauri (productName, identifier, sidecar, …)
│   ├── capabilities/
│   │   └── default.json     # Permissions Tauri (shell, opener)
│   ├── src/
│   │   └── main.rs          # Point d'entrée Rust (sidecar, splash, menu, health)
│   ├── frontend/
│   │   └── index.html       # Splash screen FR (include_str! → data URI)
│   ├── icons/               # Icônes toutes tailles (.icns, .ico, PNG)
│   └── binaries/
│       └── tablerreur-backend-aarch64-apple-darwin  # Sidecar PyInstaller
├── scripts/
│   ├── generate_icon.py     # Génère les icônes PNG (lettre T, fond bleu)
│   └── build_sidecar.py     # Package le sidecar PyInstaller
├── tests/                   # pytest (core uniquement, pas de Qt)
├── docs/                    # architecture.md, formats.md, nakala.md, AGENT_README.md
├── run.py                   # Lancement dev Qt sans install (legacy)
├── tablerreur-backend.spec  # Spec PyInstaller pour le sidecar
└── pyproject.toml           # Hatch, dépendances
```

### Principe fondamental

Le **core** est headless (Python pur, sans Qt, sans framework web). Il est importé par :
- `ui/` (PySide6) — ancienne interface, **abandonnée**, ne plus y toucher
- `web/` (FastAPI) — interface active, partagée entre Tauri desktop et déploiement online futur

**Règle absolue** : ne jamais introduire de dépendance Qt ou PySide6 dans `core/`. Ne jamais introduire de dépendance FastAPI dans `core/`.

---

## Migration en cours : Qt → Tauri

### Contexte
L'app Qt souffrait de segfaults (PySide6) et de difficultés de packaging. Migration vers :
1. **Tauri** (app desktop) : fenêtre native embarquant l'UI web, backend Python en sidecar
2. **Déploiement online** : même UI web + FastAPI sur serveur (Phase D, pas encore faite)

### Statut des phases

**Phase A — Launcher local** ✅ FAIT
- `python -m spreadsheet_qa.web` : port auto, démarrage FastAPI, ouverture navigateur
- `GET /health` → `{"status": "ok", "version": "..."}`
- Logs dans stdout

**Phase B — Projet Tauri** ✅ FAIT
- `src-tauri/` : config Tauri v2, Cargo.toml, tauri.conf.json
- Sidecar Python packagé via PyInstaller (`build_sidecar.py`, spec PyInstaller)
- Tauri lance le sidecar sur un port libre (8400–8500), poll `/health` avant navigation
- Splash screen HTML FR (data URI via `include_str!`, sans dépendance fichier)
- Menu natif : Fichier (Quitter Cmd+Q) + Aide (Vérifier les mises à jour)
- Icône : lettre T sur fond bleu #2563eb (`.icns`, `.ico`, PNG toutes tailles)
- `.dmg` généré en mode debug (non signé)

**Phase C — Parité online/offline** EN COURS
- ✅ Config par colonne complète (13 presets, Oui/Non, listes, regex, etc.)
- ✅ Aperçu temps réel dans le panneau de config
- ✅ Badges sur colonnes configurées, résumé avant étape suivante
- ✅ Surlignage cellules en erreur dans l'aperçu
- 📋 Import YAML de template custom depuis l'UI
- 📋 Sélection de modèle depuis l'UI (actuellement dans le formulaire upload)

**Phase D — Déploiement online** PAS ENCORE FAIT
- Dockerfile à créer
- Limites upload (taille, types MIME)
- TTL/purge déjà présent dans `jobs.py`

### Ce qui reste à faire

- Signing macOS (certificat Apple Developer pour distribuer le .dmg)
- Auto-update Tauri (Tauri updater plugin)
- Vocabulaires distants NAKALA (nakala_api.py existe, pas encore intégré aux règles)
- Dockerfile + déploiement online
- Menu Aide → ouvrir URL GitHub releases (actuellement item présent mais non câblé)

---

## Règles de validation disponibles

### Règles génériques — Hygiène (`hygiene.py`)

| rule_id | Description |
|---|---|
| `generic.hygiene.leading_trailing_space` | Espaces en début/fin de valeur |
| `generic.hygiene.multiple_spaces` | Espaces multiples consécutifs |
| `generic.hygiene.invisible_chars` | Caractères invisibles (U+200B, U+FEFF, etc.) |
| `generic.hygiene.unicode_chars` | Caractères Unicode suspects (guillemets courbes, tirets fantaisie…) |

### Règles génériques — Structure

| rule_id | Fichier | Description |
|---|---|---|
| `generic.duplicate_rows` | `duplicates.py` | Lignes entièrement dupliquées |
| `generic.unique_column` | `duplicates.py` | Valeurs dupliquées dans une colonne marquée `unique` |
| `generic.soft_typing` | `soft_typing.py` | Colonne majoritairement d'un type → valeurs aberrantes signalées (threshold effectif) |
| `generic.unexpected_multiline` | `multiline.py` | Retours à la ligne dans une colonne non marquée `multiline_ok` |
| `generic.pseudo_missing` | `pseudo_missing.py` | Valeurs pseudo-manquantes (NA, N/A, null, -, …) |

### Règles génériques — Contraintes par colonne (nouvelles)

| rule_id | Fichier | Description |
|---|---|---|
| `generic.required` | `required.py` | Cellule vide dans une colonne marquée `required: true` |
| `generic.content_type` | `content_type.py` | Type de contenu : `integer`, `decimal`, `date`, `email`, `url` |
| `generic.regex` | `regex_rule.py` | Valeur ne correspond pas à l'expression régulière configurée |
| `generic.allowed_values` | `allowed_values.py` | Valeur hors liste autorisée (supporte aussi le mode liste avec séparateur) |
| `generic.length` | `length.py` | Longueur inférieure à `min_length` ou supérieure à `max_length` |
| `generic.forbidden_chars` | `forbidden_chars.py` | Présence de caractères interdits dans la valeur |
| `generic.case` | `case_rule.py` | Casse non conforme (`upper`, `lower`, `title`) |
| `generic.list_items` | `list_items.py` | Éléments d'une liste (séparateur configurable) : vides, non-uniques, hors bornes, hors valeurs autorisées |
| `generic.rare_values` | `rare_values.py` | Valeur apparaissant moins souvent que le seuil (suspicion de faute de saisie) |
| `generic.similar_values` | `similar_values.py` | Groupes de valeurs très proches (variantes probables) |

### Règles NAKALA (`nakala_rules.py`)

| rule_id | Description |
|---|---|
| `nakala.created_format` | Format de date W3C-DTF pour le champ dcterms:created |
| `nakala.deposit_type` | Type de dépôt NAKALA valide |
| `nakala.language` | Code langue ISO 639 valide |
| `nakala.license` | Licence NAKALA valide |

---

## UI web — état actuel

### Workflow en 5 étapes

1. **Téléverser** — upload CSV/XLSX, options d'import (encodage, délimiteur, ligne d'en-tête), choix du modèle de validation
2. **Configurer** — configuration par colonne, tableau d'aperçu interactif, panneau inline
3. **Correctifs** — application des correctifs d'hygiène (trim, espaces, NBSP, invisibles, Unicode, retours ligne), aperçu avant application
4. **Valider** — lancement de la validation, résumé par sévérité
5. **Résultats** — liste paginée/filtrée des problèmes, téléchargement des exports

### Configuration par colonne

- Panneau inline au clic sur l'en-tête de colonne
- Pré-remplissage depuis le modèle de validation sélectionné
- **13 presets de format** regroupés par catégorie :
  - Généraux : Année, Oui/Non, Alphanumérique, Lettres uniquement, Entier positif
  - Identifiants SHS : DOI, ORCID, ARK, ISSN
  - Dates : Date W3C-DTF, Date ISO stricte
  - Codes : Langue ISO 639
  - Avancé : Regex personnalisée
- Oui/Non avec mapping personnalisable (vraies/fausses valeurs)
- Liste (séparateur configurable) avec options : éléments uniques, interdire vides, min/max items
- Valeurs autorisées verrouillées (`allowed_values_locked`) — liste non modifiable depuis template
- Détection de valeurs rares (seuil configurable)

### Fonctionnalités UX avancées

- **Aperçu temps réel** : 3 exemples OK / 3 exemples en erreur avec message, debounce 300ms, endpoint `POST /preview-rule`
- **Badges sur colonnes configurées** : point vert `●` sur les `<th>`, tooltip avec résumé de la config
- **Résumé de configuration** : tableau récapitulatif avant passage à l'étape suivante, avec bouton Modifier / Continuer
- **Surlignage des cellules en erreur** : si validation déjà effectuée, les `<td>` en erreur sont colorés par sévérité (rouge/orange/violet) avec tooltip message, endpoint `GET /preview-issues`

### Design CSS

- Variables CSS cohérentes (primary, success, error, warning, suspicion, bg, surface, border, text)
- Typographie : system-ui, 15px, line-height 1.6
- Boutons : border-radius 6px, transitions 0.15s
- Tableaux : zebra striping, en-têtes #f1f5f9
- Responsive : panneau config pleine largeur < 768px, tableau d'aperçu scrollable horizontalement

---

## Tauri — état actuel

- **App desktop macOS** (aarch64-apple-darwin) via Tauri v2
- **Sidecar Python** packagé avec PyInstaller (~38 Mo, script `scripts/build_sidecar.py`)
- **Splash screen** HTML FR embarqué en `data:` URI via `include_str!` (évite les problèmes de chemin en dev)
- **Menu natif macOS** : Fichier → Quitter (Cmd+Q) ; Aide → Vérifier les mises à jour (non câblé)
- **Port dynamique** : Tauri cherche un port libre entre 8400 et 8500, le passe au sidecar
- **Health check** : poll TCP toutes les 200ms jusqu'à ce que le sidecar réponde, timeout configurable
- **Icône** : lettre T blanche sur fond bleu #2563eb (générée par `scripts/generate_icon.py`)
- **Distribution** : `.dmg` (macOS) ; sur Windows : installateur NSIS (`.exe`) et MSI (`.msi`), langue WiX en français (fr-FR)
- **Distribution macOS** : `.dmg` généré en mode debug — **non signé** (signing macOS à faire)
- **Démarrage** : ~25–37s (extraction PyInstaller onefile + init Python + chargement pandas)
- **Identifiant** : `com.tablerreur.desktop`, version 0.1.0

### Release Windows (installateur)

Pour produire une release Windows avec installateur :

1. **Sur une machine Windows** : installer les prérequis (Rust, Node.js, Python 3, Visual Studio Build Tools ou équivalent pour le toolchain MSVC).
2. À la racine du dépôt : `npm install` puis `npm run build:windows`.
   - Le script exécute `python scripts/build_sidecar.py`, puis `npm run tauri build`, puis `python scripts/build_portable_exe.py` (bundle portable : zip + exe tout-en-un si 7-Zip disponible).
3. Les artefacts sont dans `src-tauri/target/release/bundle/` :
   - **NSIS** : `nsis/Tablerreur_0.1.0_x64-setup.exe` (installateur classique)
   - **MSI** : `msi/Tablerreur_0.1.0_x64_fr-FR.msi` (installateur MSI, langue française)
   - **Portable** : `portable/Tablerreur_0.1.0_x64_portable.zip` (à extraire puis lancer `tablerreur.exe`) et éventuellement `portable/Tablerreur_0.1.0_x64_portable.exe` (un seul .exe qui embarque tout, si 7-Zip est installé)

L’installateur NSIS télécharge WebView2 au besoin (connexion internet requise lors de l’installation sauf si mode offline configuré). Voir `docs/build-windows.md` pour les détails.

**Publication sur GitHub** : en créant une release (tag, ex. `v0.1.0`), le workflow `.github/workflows/release-windows.yml` build l’app Windows et attache les .exe/.msi/.zip à la release ; les utilisateurs peuvent alors télécharger le .exe directement depuis GitHub (onglet Releases → Assets).

---

## Conventions de code

### Nommage
- Modules : `snake_case` (ex. `issue_store.py`, `template_manager.py`)
- Classes : `PascalCase` avec suffixes (`*Controller`, `*Rule`, `*Exporter`, `*Manager`)
- Règles : `rule_id` en hiérarchie pointée (ex. `generic.hygiene.leading_trailing_space`)
- Null objects : `NullProjectManager`, `NullPatchWriter` (no-op quand pas de contexte)

### Langue
- **Code** (noms de variables, fonctions, classes, commentaires techniques) : anglais
- **Tout texte visible par l'utilisateur** (UI, messages, exports, rapports) : français
- **Glossaire FR** : voir `ui/i18n.py` — utiliser `t(key)` pour toute chaîne affichée dans l'UI Qt (legacy)
- Ne jamais laisser de chaîne anglaise dans l'interface web

### Architecture
- `core/` : Python pur. Pas d'import Qt, pas d'import FastAPI. Testable unitairement.
- `web/` : FastAPI. Importe `core/`. Gère HTTP, jobs, fichiers statiques.
- `ui/` : PySide6 (legacy). **Ne pas y ajouter de fonctionnalités.**
- Tests : `pytest`. Fixtures dans `conftest.py`. Tester le core en priorité.

### Données
- DataFrame pandas, dtype string pour toutes les cellules
- CSV export : délimiteur `;`, quote `"`, UTF-8
- Config : YAML (templates, project.yml, exceptions)
- Patches : JSON (work/patches/*.json)
- Actions log : JSONL (work/actions_log.jsonl)
- Jobs web : en mémoire (TTL 1h), DataFrame sérialisé en pickle

---

## Modèles de données clés (core/models.py)

- **Severity** : `ERROR` > `WARNING` > `SUSPICION`
- **IssueStatus** : `OPEN`, `FIXED`, `IGNORED`, `EXCEPTED`
- **Issue** : id (sha256 court, déterministe), rule_id, severity, status, row, col, message, suggestion
- **Patch** : patch_id, row, col, old_value, new_value, issue_id, timestamp
- **DatasetMeta** : file_path, encoding, delimiter, sheet_name, header_row, fingerprint

---

## Ce qu'il ne faut PAS faire

1. **Ne pas modifier `core/`** pour y ajouter des dépendances UI ou web
2. **Ne pas ajouter de fonctionnalités dans `ui/`** (PySide6) — abandonné
3. **Ne pas casser les tests existants** — lancer `pytest` avant de valider
4. **Ne pas introduire de chaînes anglaises** dans l'interface utilisateur
5. **Ne pas utiliser un ORM ou une base de données** — le stockage est fichier (YAML, JSON, JSONL)
6. **Ne pas changer le délimiteur CSV** — c'est `;` partout (convention FR)

---

## Commandes utiles

```bash
# Lancer le serveur web standalone (port auto + navigateur)
python -m spreadsheet_qa.web

# Lancer le serveur sur un port spécifique (mode sidecar Tauri)
python -m spreadsheet_qa.web --port 8400

# Lancer les tests
pytest

# Lancer les tests d'un module spécifique
pytest tests/test_engine.py -v

# Développement Tauri (fenêtre native + rechargement auto)
npm run tauri dev

# Build Tauri (plateforme courante : .dmg sur macOS, .exe/.msi sur Windows)
npm run tauri build

# Release Windows (sur machine Windows : sidecar + installateurs NSIS et MSI)
npm run build:windows

# Générer les icônes (à relancer si l'icône change)
python scripts/generate_icon.py

# Packager le sidecar Python (PyInstaller)
python scripts/build_sidecar.py

# Lancer l'app Qt (legacy — debug uniquement)
python run.py
```

---

## Fichiers de référence

| Besoin                        | Fichier                              |
|-------------------------------|--------------------------------------|
| Spec produit                  | SPEC.md                              |
| Architecture détaillée        | docs/architecture.md                 |
| Build release Windows         | docs/build-windows.md                |
| Formats (CSV, patches…)       | docs/formats.md                      |
| Overlay NAKALA                | docs/nakala.md                       |
| Guide agent complet           | docs/AGENT_README.md                 |
| Liste des règles              | core/rules/*.py                      |
| Glossaire FR (legacy Qt)      | ui/i18n.py                           |
| Signaux Qt (legacy)           | ui/signals.py                        |
| Backlog fonctionnel           | BACKLOG.md                           |
