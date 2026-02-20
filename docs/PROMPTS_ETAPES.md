# Prompts par étape — Migration Tablerreur Qt → Tauri

> Copier-coller ces prompts dans Claude Code (terminal) ou l'agent Cursor.
> Chaque prompt est autonome mais s'appuie sur CLAUDE.md et .cursorrules.
> Les exécuter dans l'ordre.

---

## Étape A1 — Endpoint /health

```
Lis CLAUDE.md pour le contexte du projet.

Dans web/app.py, ajoute un endpoint GET /health qui retourne :
{"status": "ok", "version": "<version du paquet>"}

La version doit venir de spreadsheet_qa.__version__ ou du pyproject.toml.
Si __version__ n'existe pas encore, crée-le dans __init__.py.

Ne casse aucun endpoint existant. Lance pytest pour vérifier.
```

---

## Étape A2 — Launcher standalone

```
Lis CLAUDE.md pour le contexte du projet.

Crée le fichier src/spreadsheet_qa/web/launcher.py qui permet de lancer le serveur web en mode standalone :

1. Trouve un port TCP libre (range 8400-8500, fallback aléatoire)
2. Démarre uvicorn avec l'app FastAPI de web/app.py sur ce port
3. Attend que GET /health réponde OK (polling avec timeout 10s)
4. Ouvre le navigateur par défaut sur http://localhost:{port}
5. Affiche dans le terminal :
   "Tablerreur est lancé : http://localhost:{port}"
   "Fermez cette fenêtre (ou Ctrl+C) pour arrêter."
6. Gère SIGINT/SIGTERM proprement (shutdown uvicorn)

Ajoute aussi le point d'entrée pour que `python -m spreadsheet_qa.web` appelle ce launcher.
Ça veut dire créer web/__main__.py qui appelle launcher.main().

Textes affichés : en français.
Pas de dépendance à Qt/PySide6.
Lance pytest pour vérifier que rien n'est cassé.
```

---

## Étape A3 — Vérification parité UI web

```
Lis CLAUDE.md pour le contexte du projet.

Compare les fonctionnalités de l'UI Qt (ui/) avec l'UI web (web/).
Liste dans un fichier docs/web_parity.md :

1. Ce qui est disponible dans les deux (✅)
2. Ce qui est dans Qt mais pas dans le web (❌)
3. Ce qui est dans le web mais pas dans Qt (🆕)

Catégories à vérifier :
- Chargement (CSV, XLSX, choix feuille, encodage, délimiteur, ligne d'en-tête)
- Templates (sélection builtin, import YAML, overlay NAKALA)
- Correctifs typiques (espaces, doubles espaces, invisibles, Unicode, retours ligne) + aperçu
- Validation (lancement, revalidation partielle, affichage issues)
- Exports (rapport TXT, problèmes.csv, export XLSX)
- Projet (ouverture, patches, undo/redo, exceptions)

Ne modifie aucun code, c'est un audit seulement.
```

---

## Étape B1 — Initialisation Tauri

```
Lis CLAUDE.md pour le contexte du projet.

Initialise un projet Tauri v2 dans le repo Tablerreur :

1. Crée le dossier src-tauri/ avec la structure minimale (Cargo.toml, tauri.conf.json, src/main.rs)
2. Dans tauri.conf.json :
   - productName: "Tablerreur"
   - identifier: un identifiant de type com.tablerreur.app
   - window.title: "Tablerreur"
   - window.width: 1200, height: 800
   - Pas de devUrl pour l'instant, on configurera le sidecar après
3. main.rs : juste le boilerplate Tauri v2 minimal qui ouvre une fenêtre
4. Ajoute les icônes placeholder dans src-tauri/icons/

Ne touche pas au code Python.
Ne lance pas `cargo build` (on n'a peut-être pas Rust installé), mais la config doit être valide.
Documente dans un commentaire en haut de main.rs ce qui reste à faire (sidecar).
```

---

## Étape B2 — Configuration sidecar

```
Lis CLAUDE.md pour le contexte du projet.

Configure Tauri pour lancer le backend Python comme sidecar :

1. Dans tauri.conf.json, ajoute la config externalBin pour un sidecar nommé "tablerreur-backend"
   (le binaire sera dans src-tauri/binaries/)
2. Dans main.rs, ajoute le code pour :
   a. Lancer le sidecar au démarrage avec un port libre (passé en argument)
   b. Attendre que GET http://localhost:{port}/health réponde (polling, timeout 15s)
   c. Charger http://localhost:{port} dans la webview
   d. Si le backend ne démarre pas : afficher une fenêtre d'erreur EN FRANÇAIS avec un diagnostic copiable
   e. Quand la fenêtre se ferme : kill le sidecar proprement
3. Ajoute un menu "Aide" avec un item "Vérifier les mises à jour" qui ouvre une URL (placeholder)

Tout message affiché à l'utilisateur : en français.
Commente le code Rust clairement (en anglais pour les commentaires techniques).
```

---

## Étape B3 — Script de packaging sidecar

```
Lis CLAUDE.md pour le contexte du projet.

Crée un script scripts/build_sidecar.py (ou .sh) qui :

1. Utilise PyInstaller pour packager `python -m spreadsheet_qa.web` en un seul exécutable
   - Inclut les resources/templates/ dans le bundle
   - Inclut les fichiers statiques de web/static/
   - Nom de sortie : tablerreur-backend (ou tablerreur-backend.exe sur Windows)
2. Copie l'exécutable dans src-tauri/binaries/ avec le bon suffixe triple pour Tauri :
   - Linux : tablerreur-backend-x86_64-unknown-linux-gnu
   - macOS : tablerreur-backend-x86_64-apple-darwin (+ aarch64 si M1)
   - Windows : tablerreur-backend-x86_64-pc-windows-msvc.exe
3. Affiche un résumé (taille, chemin, triple)

Le script doit fonctionner sur la plateforme courante (pas de cross-compilation).
Ajoute un requirements-build.txt avec pyinstaller si nécessaire.
```

---

## Étape C1 — Préparation déploiement online

```
Lis CLAUDE.md pour le contexte du projet.

Prépare le déploiement online de l'UI web :

1. Dans web/app.py, ajoute :
   - Limite upload fichier : 50 Mo max (configurable via variable d'env TABLERREUR_MAX_UPLOAD_MB)
   - Types acceptés : .csv, .xlsx, .xls uniquement
   - Message d'erreur en français si dépassé ou type refusé
2. Vérifie que le TTL/purge des jobs est bien actif (déjà dans jobs.py normalement)
3. Crée un Dockerfile simple :
   - Base python:3.11-slim
   - Install des dépendances
   - Expose port 8000
   - CMD : uvicorn spreadsheet_qa.web.app:app --host 0.0.0.0 --port 8000
4. Crée un docker-compose.yml minimal (service unique)

Pas de base de données, pas de Redis — les jobs restent en mémoire (TTL 1h).
Lance pytest pour vérifier.
```

---

## Prompt de debug générique

```
Lis CLAUDE.md pour le contexte du projet.

J'ai un problème : [DÉCRIS LE PROBLÈME ICI]

Règles :
- Ne modifie pas core/ sauf si le bug est dedans
- Ne touche pas à ui/ (PySide6 legacy)
- Si le fix est dans web/, vérifie que /health fonctionne toujours
- Lance pytest après le fix
- Messages d'erreur en français si visibles par l'utilisateur
```

---

## Prompt de refactoring

```
Lis CLAUDE.md pour le contexte du projet.

Je veux refactorer [MODULE/FICHIER].

Avant de coder :
1. Lis le fichier actuel entièrement
2. Identifie les dépendances (qui importe ce module ?)
3. Propose un plan de refactoring en 3-5 points
4. Attends ma validation avant d'écrire du code

Contraintes :
- Ne casse pas les tests (pytest)
- Respecte la séparation core / web / ui
- Pas de nouvelle dépendance sans justification
```
