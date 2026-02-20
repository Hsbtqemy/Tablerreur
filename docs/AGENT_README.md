# Tablerreur — Guide pour agents et développeurs

Ce document décrit le programme, sa structure, les conventions de nommage et les flux de données pour permettre à un agent (ou un humain) de comprendre le fonctionnement et la profondeur du projet sans parcourir tout le code.

---

## 1. Vue d’ensemble

**Tablerreur** (nom du produit ; paquet Python `spreadsheet_qa`) est une application desktop cross‑plateforme (macOS / Windows / Linux) pour :

- **Charger** des feuilles CSV ou XLSX (détection encodage/délimiteur, choix de la ligne d’en-tête).
- **Valider** le contenu avec des règles configurables (hygiène, doublons, typage, etc.).
- **Corriger** les cellules (manuel ou Find & Fix en masse) avec undo/redo.
- **Exporter** les données nettoyées (XLSX, CSV `;`) et des rapports (TXT, issues.csv).

Le **core** est en Python pur (sans Qt) pour permettre tests et usage headless. L’**UI** utilise PySide6 (Qt) et communique avec le core via des contrôleurs et un bus de signaux.

---

## 2. Stack et points d’entrée

| Élément | Détail |
|--------|--------|
| **Langage** | Python 3.11+ |
| **GUI** | PySide6 (Qt 6) |
| **Données** | pandas (DataFrame, dtype string pour les cellules) |
| **Config** | YAML (templates, project.yml, exceptions) |
| **Layout** | `src/` : code sous `src/spreadsheet_qa/` |

**Lancement :**

- `python -m spreadsheet_qa` ou `spreadsheet-qa` (script déclaré dans `pyproject.toml`).
- Depuis la racine du projet sans install : `python run.py` (ajoute `src/` à `sys.path`).

Point d’entrée réel : `spreadsheet_qa.__main__:main` → `create_app()` (QApplication + MainWindow) → `window.show()` puis `app.exec()`.

---

## 3. Structure des répertoires

```
Tablerreur/
├── src/spreadsheet_qa/           # Code source du paquet
│   ├── __main__.py               # Entry point (main, platform fixes, diagnostics)
│   ├── __init__.py
│   ├── core/                     # Couche métier (sans Qt)
│   │   ├── models.py             # Dataclasses : Issue, Patch, DatasetMeta, Severity, etc.
│   │   ├── engine.py             # ValidationEngine (orchestre les règles)
│   │   ├── rule_base.py          # Rule (ABC), RuleRegistry (singleton)
│   │   ├── rules/                # Règles concrètes (hygiene, duplicates, …)
│   │   ├── issue_store.py        # Stockage des Issue en mémoire (index par id, col, (row,col))
│   │   ├── dataset.py            # DatasetLoader, preview_header_rows, get_xlsx_sheet_names
│   │   ├── template.py           # TemplateLoader (load + expand_wildcards)
│   │   ├── template_manager.py   # TemplateManager (builtin / user / project), compile_config
│   │   ├── project.py            # ProjectManager, NullProjectManager (project.yml, actions_log, …)
│   │   ├── patch.py              # PatchWriter, NullPatchWriter (work/patches/*.json)
│   │   ├── commands.py           # Command (ABC), ApplyCellFixCommand, BulkCellFixCommand, SetIssueStatusCommand
│   │   ├── history.py            # CommandHistory (undo/redo, max 500)
│   │   ├── exporters.py          # XLSXExporter, CSVExporter, TXTReporter, IssuesCSVExporter
│   │   ├── nakala_api.py         # NakalaClient (vocabulaires NAKALA)
│   │   ├── resources.py         # Chemins builtin (templates)
│   │   └── text_utils.py         # Utilitaires texte si présents
│   ├── ui/                       # Couche interface (PySide6)
│   │   ├── app.py                # create_app(), stylesheet
│   │   ├── signals.py            # AppSignals (singleton), get_signals()
│   │   ├── main_window.py        # MainWindow (toolbar, docks, central table)
│   │   ├── i18n.py               # t(key), severity_label, status_label, …
│   │   ├── controllers/          # LoadController, ValidationController, FixController, ExportController, ProjectController
│   │   ├── dialogs/              # LoadDialog, ExportDialog, TemplateLibraryDialog, TemplateEditorDialog
│   │   ├── panels/               # IssuesPanel, FindFixDrawer
│   │   └── table/                # SpreadsheetTableModel, SpreadsheetTableView
│   ├── web/                      # (Optionnel) API / jobs pour usage web
│   │   ├── app.py
│   │   └── jobs.py
│   └── resources/
│       └── templates/            # YAML builtin + legacy
│           ├── builtin/          # generic_default, generic_strict, nakala_baseline, nakala_extended
│           ├── generic.yml
│           └── overlay_nakala.yml
├── tests/                        # pytest (conftest, test_engine, test_rules, …)
├── docs/                         # architecture.md, formats.md, nakala.md, ux.md, AGENT_README.md
├── run.py                        # Lancement sans install (PATH = src)
├── pyproject.toml                # Dépendances, scripts, hatch build
└── SPEC.md / README.md           # Spec produit et usage
```

---

## 4. Architecture en couches

- **UI** : `main_window`, `controllers`, `dialogs`, `panels`, `table`, `signals`. Dépend du core (imports) mais le core ne dépend pas de Qt.
- **Core** : modèles, moteur de validation, règles, store d’issues, commandes, historique, chargement de données, templates, export, patch, projet. Aucune dépendance à PySide6.

La communication UI ↔ core passe par :

- **Controllers** : appellent le core (DatasetLoader, ValidationEngine, CommandHistory, etc.) et mettent à jour le modèle Qt / le store.
- **AppSignals** : signaux Qt globaux (singleton) pour découpler les composants (dataset_loaded, issues_updated, cell_edit_requested, etc.).

---

## 5. Conventions de nommage

### Modules / paquets

- **Snake_case** : `issue_store`, `template_manager`, `find_fix_drawer`.
- **core** = logique métier ; **ui** = interface ; **ui/controllers** = orchestration ; **ui/panels** = blocs d’UI réutilisables ; **ui/dialogs** = fenêtres modales.

### Classes

- **PascalCase** : `ValidationEngine`, `SpreadsheetTableModel`, `ApplyCellFixCommand`.
- **Suffixes courants** : `*Controller`, `*Dialog`, `*Panel`, `*Rule`, `*Exporter`, `*Writer`, `*Manager`.
- **Null / no-op** : `NullProjectManager`, `NullPatchWriter` (implémentations vides pour « pas de projet » / « pas de patches »).

### Règles de validation

- **rule_id** : hiérarchie en points, ex. `generic.hygiene.leading_trailing_space`, `nakala.license`.
- **Enregistrement** : décorateur `@registry.register` sur la classe (voir `core/rules/*.py`). Le registre est le singleton `registry` dans `rule_base.py`.

### Signaux (AppSignals)

- **Noms explicites** : `dataset_loaded`, `issues_updated`, `cell_edit_requested`, `validation_finished`, `history_changed`, `template_changed`, `issue_status_changed`, `status_message`, etc.
- Types documentés en commentaire (ex. `Signal(object)` pour `DatasetMeta`).

### Fichiers de configuration / données

- **project.yml** : métadonnées du projet (source, template, overlay, header_row, encoding, fingerprint, …).
- **work/actions_log.jsonl** : une ligne JSON par action (fix, undo, redo, …).
- **work/patches/<patch_id>.json** : un correctif cellule (row, col, old_value, new_value, issue_id, …).
- **work/exceptions.yml** : exceptions / statuts utilisateur (cell_exceptions, value_exceptions, column_ignores, …).
- **templates/** (dans le projet) : YAML de templates projet ; **builtin** dans `resources/templates/builtin/`.

---

## 6. Flux de données principaux

### Chargement

- Utilisateur : Ouvrir → **LoadDialog** (fichier, ligne d’en-tête, feuille, encodage, délimiteur).
- **LoadController.load_file()** → **DatasetLoader.load()** (chardet, csv.Sniffer, pandas) → `(DataFrame, DatasetMeta)`.
- **SpreadsheetTableModel** reçoit une **référence directe** au DataFrame (pas de copie).
- **AppSignals.dataset_loaded** émet `DatasetMeta` → **ValidationController** déclenche une validation complète.

### Validation

- **ValidationController.run_full()** ou **run_partial(columns)**.
- Travail asynchrone : **QRunnable** (QThreadPool) qui appelle **ValidationEngine.validate(df, columns, config)**.
- Le moteur parcourt les règles enregistrées, pour chaque règle (et colonne si `per_column`) appelle **rule.check(df, col, config)** → `list[Issue]`.
- De retour sur le thread principal : **IssueStore.replace_all()** ou **replace_for_columns()**, puis **AppSignals.issues_updated**, rafraîchissement du modèle de table et du panneau Issues.

### Correction (Fix)

- Édition cellule dans la vue → signal **cell_edit_requested(row, col, new_value)** → **FixController._on_cell_edit**.
- **FixController.apply_fix()** crée **ApplyCellFixCommand**, l’exécute via **CommandHistory.push()** : modification du DataFrame, **IssueStore.set_status(issue_id, FIXED)**, **PatchWriter.write(patch)**, **ProjectManager.append_action_log()** si projet ouvert.
- Puis **SpreadsheetTableModel.refresh_cell()**, **patch_applied**, **ValidationController.run_partial([col])**, **history_changed**.

### Undo / Redo

- **CommandHistory** : deux deques (undo, redo), profondeur max 500.
- Undo : pop la dernière commande, **cmd.undo()** (remet ancienne valeur, rouvre l’issue, déplace le patch dans undone/), puis refresh et signaux.

### Export

- Utilisateur : Export → **ExportDialog** (choix répertoire, options XLSX/CSV/rapport/issues.csv).
- **ExportController** utilise **XLSXExporter**, **CSVExporter**, **TXTReporter**, **IssuesCSVExporter** (délimiteur CSV toujours `;`, voir docs/formats.md).

---

## 7. Modèles de données (core/models.py)

- **Severity** : `ERROR`, `WARNING`, `SUSPICION` (ordre pour tri).
- **IssueStatus** : `OPEN`, `FIXED`, `IGNORED`, `EXCEPTED`.
- **ColumnKind** : `free_text_short`, `free_text_long`, `controlled`, `structured`, `list`.
- **DatasetMeta** : file_path, encoding, delimiter, sheet_name, header_row, skip_rows, original_shape, column_order, fingerprint.
- **Issue** : id (déterministe, sha256 court), rule_id, severity, status, row, col, original, message, suggestion, extra. Fabrique : **Issue.create()** / **Issue.make_id()**.
- **Patch** : patch_id, action_id, row, col, old_value, new_value, issue_id, timestamp ; **to_dict** / **from_dict** pour JSON.
- **ActionLogEntry** : action_id, timestamp, action_type, scope, params, stats, patch_ids ; **to_dict** pour JSONL.

---

## 8. Règles de validation

- **Base** : `Rule` (ABC) dans `rule_base.py` avec `rule_id`, `name`, `default_severity`, `per_column`, et **check(df, col, config) → list[Issue]**.
- **Registry** : `RuleRegistry` singleton ; **all_rules()**, **get(rule_id)**. Les sous-modules dans `core/rules/` importés pour que les `@registry.register` s’exécutent.
- **Config** : dict par règle (severity, enabled, seuils, etc.) et par colonne (unique, multiline_ok, rule_overrides). Fourni par les **templates** (voir section 9).
- **Règles globales** (`per_column=False`) : ex. doublons de lignes ; exécutées une fois par validation complète (ignorées en revalidation partielle).

---

## 9. Templates et configuration de validation

- **TemplateLoader** (`core/template.py`) : **load(base_path, overlay_path)** (YAML safe_load + deep_merge), **expand_wildcards(config, column_names)** pour résoudre `columns` et `column_groups` (glob) en une config par colonne.
- **TemplateManager** (`core/template_manager.py`) : découverte des templates **builtin** (ressources paquet), **user** (répertoire config plateforme), **project** (dossier projet). **compile_config(generic_id, overlay_id, column_names)** retourne le dict attendu par **ValidationEngine.validate(..., config=...)**.
- Structure config typique : `rules` (rule_id → options), `columns` (nom_colonne → options dont `unique`, `multiline_ok`, `rule_overrides`), éventuellement `column_groups` (patterns glob). Le moteur fusionne rule + column + rule_overrides par (règle, colonne).

---

## 10. Projet (dossier Tablerreur)

- **ProjectManager** : crée/gère la structure (work/patches, work/patches/undone, reports, exports, input, templates), **project.yml**, **work/actions_log.jsonl**, **work/exceptions.yml**, copie des fichiers d’entrée dans **input/**.
- **NullProjectManager** : utilisé quand aucun dossier projet n’est ouvert (pas d’écriture projet).
- **PatchWriter** : écrit/supprime les JSON dans **work/patches/** ; **NullPatchWriter** pour ne pas écrire de patches.

---

## 11. Threading et accès aux données

- **Validation** : exécutée dans un **QRunnable** (pool Qt). Seul le thread principal modifie **IssueStore** et le modèle Qt (via signaux en QueuedConnection).
- **IssueStore** : non thread-safe ; accès uniquement depuis le thread principal.
- **DataFrame** : référence partagée ; les commandes de fix modifient **le même** DataFrame.

---

## 12. UI : fenêtre principale et composants

- **MainWindow** : barre d’outils (Ouvrir, Valider, Find & Fix, Undo/Redo, Export, etc.), zone centrale = **SpreadsheetTableView**, docks = **IssuesPanel** (droite), **FindFixDrawer** (bas, masqué par défaut), barre de statut.
- **SpreadsheetTableModel** : **référence directe** au DataFrame ; **data()** utilise **IssueStore** pour la couleur de fond (severity) et le tooltip ; **setData()** n’écrit pas dans le df, émet **cell_edit_requested**.
- **SpreadsheetTableView** : **scroll_to_cell(row, col)** pour aller à une cellule (ex. après clic sur une issue). Vérifications de bornes pour éviter indices invalides (compatibilité accessibilité Qt).
- **Internationalisation** : **ui/i18n.py** — **t(key)** pour les chaînes ; **severity_label**, **status_label**, etc.

---

## 13. Export et formats

- **CSV** : délimiteur `;`, quote `"`, QUOTE_MINIMAL, UTF-8 (ou BOM). Voir **docs/formats.md**.
- **XLSX** : openpyxl, une feuille « Data ».
- **Rapport TXT** : résumé par sévérité, colonnes les plus affectées, types d’issues, détails.
- **issues.csv** : liste des issues (id, severity, status, rule_id, row, column, message, original_value, suggestion, …).

---

## 14. Tests

- **pytest** ; `tests/conftest.py` : fixtures (**simple_df**, **empty_df**, **dup_rows_df**, etc.).
- **test_engine.py**, **test_rules.py** : moteur et règles (core uniquement).
- **test_commands.py**, **test_patch.py**, **test_export.py**, **test_import.py** : commandes, patches, export, chargement.
- **pytest-qt** pour les tests UI si nécessaire.

---

## 15. Points sensibles pour les agents

- **Ne pas importer Qt dans le core** : le core doit rester utilisable sans affichage.
- **IssueStore** : uniquement sur le thread principal ; les mises à jour après validation passent par les signaux.
- **Index / bornes** : le modèle de table vérifie les bornes (row, col) dans **data()**, **index()**, **flags()**, **setData()**, **headerData()** pour éviter des accès hors limites (notamment avec l’accessibilité Qt sur macOS).
- **Templates** : la config de validation utilisée par le moteur vient de **TemplateManager.compile_config()** (ou équivalent) alimenté par le contrôleur de chargement/projet ; sans cela, **config** peut être vide et certaines règles (ex. unique_column, unexpected_multiline) ne s’appliquent pas comme prévu.
- **Projet** : sans dossier projet ouvert, **ProjectManager** est remplacé par **NullProjectManager** et **PatchWriter** par **NullPatchWriter** ; les patches et l’actions_log ne sont pas persistés.

---

## 16. Références rapides

| Besoin | Fichier / élément |
|--------|--------------------|
| Spécification produit | SPEC.md |
| Architecture détaillée | docs/architecture.md |
| Formats (CSV, project.yml, patches) | docs/formats.md |
| Overlay NAKALA | docs/nakala.md |
| Signaux disponibles | ui/signals.py (classe AppSignals) |
| Liste des règles | core/rules/*.py + rule_base.registry.all_ids() |
| Entrée programme | __main__.py → main() ; ui/app.py → create_app() |

Ce document et les fichiers listés ci-dessus suffisent pour comprendre le fonctionnement et la profondeur du projet sans lire tout le code.
