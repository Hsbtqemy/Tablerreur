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
│   ├── __main__.py          # Entry point
│   ├── core/                # Métier pur (AUCUNE dépendance Qt/UI)
│   │   ├── models.py        # Issue, Patch, DatasetMeta, Severity, IssueStatus…
│   │   ├── engine.py        # ValidationEngine
│   │   ├── rule_base.py     # Rule ABC + RuleRegistry singleton
│   │   ├── rules/           # Règles concrètes (hygiene, duplicates…)
│   │   ├── issue_store.py   # Stockage issues en mémoire
│   │   ├── dataset.py       # DatasetLoader (CSV/XLSX, encodage, délimiteur)
│   │   ├── template.py      # TemplateLoader (YAML, deep_merge, wildcards)
│   │   ├── template_manager.py  # Découverte templates (builtin/user/project)
│   │   ├── project.py       # ProjectManager + NullProjectManager
│   │   ├── patch.py         # PatchWriter + NullPatchWriter
│   │   ├── commands.py      # Command ABC, ApplyCellFixCommand, BulkCellFixCommand…
│   │   ├── history.py       # CommandHistory (undo/redo, max 500)
│   │   ├── exporters.py     # XLSX, CSV (;), TXT rapport, issues.csv
│   │   └── nakala_api.py    # Client vocabulaires NAKALA
│   ├── ui/                  # PySide6 — EN COURS D'ABANDON
│   │   ├── app.py           # create_app(), stylesheet
│   │   ├── signals.py       # AppSignals singleton
│   │   ├── main_window.py   # MainWindow
│   │   ├── i18n.py          # t(key), glossaire FR
│   │   ├── controllers/     # Load, Validation, Fix, Export, Project
│   │   ├── dialogs/         # Load, Export, TemplateLibrary, TemplateEditor
│   │   ├── panels/          # IssuesPanel, FindFixDrawer
│   │   └── table/           # SpreadsheetTableModel, SpreadsheetTableView
│   ├── web/                 # FastAPI — SERA LE FRONTEND (Tauri + online)
│   │   ├── app.py           # API FastAPI + static
│   │   └── jobs.py          # Jobs temporaires (TTL 1h)
│   └── resources/templates/ # YAML builtin (generic, nakala…)
├── tests/                   # pytest (core uniquement, pas de Qt)
├── docs/                    # architecture.md, formats.md, nakala.md…
├── run.py                   # Lancement dev sans install
└── pyproject.toml           # Hatch, dépendances
```

### Principe fondamental

Le **core** est headless (Python pur, sans Qt, sans framework web). Il est importé par :
- `ui/` (PySide6) — l'ancienne interface, en voie d'abandon
- `web/` (FastAPI) — la nouvelle interface, partagée entre online et Tauri

**Règle absolue** : ne jamais introduire de dépendance Qt ou PySide6 dans `core/`. Ne jamais introduire de dépendance FastAPI dans `core/`.

---

## Migration en cours : Qt → Tauri

### Contexte
L'app Qt souffre de segfaults (PySide6) et de difficultés de packaging. On migre vers :
1. **Tauri** (app desktop) : fenêtre native embarquant l'UI web, backend Python en sidecar
2. **Déploiement online** : même UI web + FastAPI sur serveur

### Ce qui existe déjà et fonctionne
- Core headless complet (validation, règles, templates, correctifs, exports)
- UI web 4 étapes FR : Téléverser → Correctifs → Valider → Résultats
- Jobs web temporaires (TTL 1h, upload/fixes/validate/download)
- i18n FR complet (glossaire + `t()`)
- Exports FR (rapport TXT, problèmes.csv, export.xlsx)

### Ce qui n'existe PAS encore (à créer)
- Aucun dossier `src-tauri/`, aucune config Tauri
- Pas de mode launcher standalone (`python -m spreadsheet_qa.web` avec port auto + navigateur)
- Pas de sidecar Python packagé
- Pas de `/health` endpoint

### Plan de migration (phases)

**Phase A — Launcher local (avant Tauri)**
1. Ajouter un mode `python -m spreadsheet_qa.web` qui :
   - Choisit un port libre
   - Démarre le serveur FastAPI
   - Ouvre le navigateur par défaut
   - Affiche "Fermez le terminal pour arrêter"
2. Ajouter `GET /health` → `{"status": "ok"}`
3. Logs dans un dossier user-friendly

**Phase B — Projet Tauri**
1. `npm create tauri-app` dans le repo (dossier `src-tauri/`)
2. Configurer le sidecar Python (exécutable packagé via PyInstaller ou Nuitka)
3. Tauri lance le sidecar au démarrage, attend `/health`
4. UI web chargée dans la webview Tauri
5. Gestion d'erreurs en français (backend non démarré → message FR + diagnostic copiable)
6. Menu "Aide" avec lien mise à jour manuelle

**Phase C — Parité online/offline**
1. Vérifier que l'UI web expose : sélection modèles + import YAML + correctifs typiques + aperçu
2. Même vocabulaire FR partout (glossaire `i18n.py`)

**Phase D — Déploiement online**
1. FastAPI + static sur serveur
2. Limites upload (taille, types)
3. TTL/purge (déjà présent)

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
- **Glossaire FR** : voir `ui/i18n.py` — utiliser `t(key)` pour toute chaîne affichée
- Ne jamais laisser de chaîne anglaise dans l'interface

### Architecture
- `core/` : Python pur. Pas d'import Qt, pas d'import FastAPI. Testable unitairement.
- `web/` : FastAPI. Importe `core/`. Gère HTTP, jobs, fichiers statiques.
- `ui/` : PySide6 (legacy). Importe `core/`. **Ne pas y ajouter de fonctionnalités.**
- Tests : `pytest`. Fixtures dans `conftest.py`. Tester le core en priorité.

### Données
- DataFrame pandas, dtype string pour toutes les cellules
- CSV export : délimiteur `;`, quote `"`, UTF-8
- Config : YAML (templates, project.yml, exceptions)
- Patches : JSON (work/patches/*.json)
- Actions log : JSONL (work/actions_log.jsonl)

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
2. **Ne pas ajouter de fonctionnalités dans `ui/`** (PySide6) — c'est en voie d'abandon
3. **Ne pas casser les tests existants** — lancer `pytest` avant de valider
4. **Ne pas introduire de chaînes anglaises** dans l'interface utilisateur
5. **Ne pas utiliser un ORM ou une base de données** — le stockage est fichier (YAML, JSON, JSONL)
6. **Ne pas changer le délimiteur CSV** — c'est `;` partout (convention FR)

---

## Commandes utiles

```bash
# Lancer l'app Qt (legacy)
python run.py

# Lancer les tests
pytest

# Lancer les tests d'un module spécifique
pytest tests/test_engine.py -v

# Futur : lancer le serveur web standalone
python -m spreadsheet_qa.web
```

---

## Fichiers de référence

| Besoin                    | Fichier                              |
|---------------------------|--------------------------------------|
| Spec produit              | SPEC.md                              |
| Architecture détaillée    | docs/architecture.md                 |
| Formats (CSV, patches…)   | docs/formats.md                      |
| Overlay NAKALA            | docs/nakala.md                       |
| Signaux Qt (legacy)       | ui/signals.py                        |
| Liste des règles          | core/rules/*.py                      |
| Glossaire FR              | ui/i18n.py                           |
| Guide agent complet       | docs/AGENT_README.md                 |
