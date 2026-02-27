# Prompt autonome — Intégration Mapala dans Tablerreur

> Faire lire par Claude Code :
> "Lis PROMPT_MAPALA_INTEGRATION.md à la racine du repo et exécute toutes les tâches."

```
Lis CLAUDE.md pour le contexte du projet Tablerreur.

On va intégrer Mapala (outil de mapping de tableur) dans la même application.
Le core Mapala est dans ~/Dev/Mapala-1/ et se compose de 3 fichiers Python purs (aucune dépendance Qt) :
- config.py (30 lignes) : exceptions + ConcatSource dataclass
- io_excel.py (213 lignes) : list_sheets, load_sheet, load_sheet_raw, save_output
- template_builder.py (292 lignes) : TemplateBuilderConfig, ZoneSpec, build_output()

L'objectif : deux onglets dans la même app (Mapala = mapper, Tablerreur = valider), même sidecar Python, même Tauri.

Fais les tâches dans l'ordre. pytest doit passer après chaque tâche.

## Tâche 1 — Copier le core Mapala

1. Crée le dossier src/spreadsheet_qa/core/mapala/
2. Copie les 3 fichiers core depuis ~/Dev/Mapala-1/ :
   - Cherche config.py, io_excel.py, template_builder.py dans le projet Mapala
   - Copie-les dans src/spreadsheet_qa/core/mapala/
3. Crée src/spreadsheet_qa/core/mapala/__init__.py avec les imports principaux :
   ```python
   from .template_builder import TemplateBuilderConfig, ZoneSpec, build_output
   from .io_excel import list_sheets, load_sheet, save_output as save_mapala_output
   from .config import ConcatSource, MapalaError
   ```
4. Vérifie que les imports fonctionnent :
   ```
   python -c "from spreadsheet_qa.core.mapala import TemplateBuilderConfig, list_sheets; print('OK')"
   ```
5. Adapte si nécessaire : les imports internes (ex: `from config import ...` → `from .config import ...`)

### Vérification :
- L'import fonctionne
- pytest passe (aucun conflit avec le code existant)

## Tâche 2 — Endpoints FastAPI pour Mapala

Dans web/app.py (ou crée un fichier web/mapala_routes.py si app.py devient trop gros), ajoute ces endpoints :

### POST /api/mapala/upload
- Upload d'un ou deux fichiers :
  - `template_file` : le fichier template (XLSX/ODS/CSV)
  - `source_file` : le fichier source à mapper
- Crée un "mapala job" (stocké dans un dict en mémoire, comme les jobs Tablerreur)
- Retourne : `{ "job_id": "...", "template_sheets": [...], "source_sheets": [...] }`

### POST /api/mapala/preview
- Body : `{ "job_id": "...", "template_sheet": "Feuil1", "source_sheet": "Sheet1", "rows": 30 }`
- Charge les deux feuilles et retourne un aperçu :
```json
{
  "template_columns": ["titre", "auteur", "date", "type"],
  "source_columns": ["Titre de l'oeuvre", "Auteur complet", "Date pub", "Catégorie"],
  "template_preview": [["val1", "val2", ...], ...],
  "source_preview": [["val1", "val2", ...], ...]
}
```

### POST /api/mapala/build
- Body : config de mapping complète (au format TemplateBuilderConfig)
```json
{
  "job_id": "...",
  "template_sheet": "Feuil1",
  "source_sheet": "Sheet1",
  "mappings": [
    {"template_col": "titre", "source_col": "Titre de l'oeuvre"},
    {"template_col": "auteur", "source_cols": ["Prénom", "Nom"], "separator": " ", "prefix": ["", ""]},
    {"template_col": "date", "source_col": "Date pub"},
    {"template_col": "type", "value": "article"}
  ],
  "output_format": "xlsx"
}
```
- Appelle build_output() avec la config
- Sauvegarde le résultat dans le job
- Retourne : `{ "job_id": "...", "rows_mapped": 150, "columns_mapped": 4 }`

### GET /api/mapala/jobs/{job_id}/download
- Retourne le fichier résultat en téléchargement
- Content-Disposition: attachment

### POST /api/mapala/jobs/{job_id}/validate
- Prend le fichier résultat de Mapala et crée un job Tablerreur avec
- C'est le pont entre Mapala et Tablerreur : mapper → valider
- Retourne : `{ "tablerreur_job_id": "..." }` pour que l'UI puisse naviguer vers la validation

### Gestion des jobs Mapala :
- Dictionnaire en mémoire : `mapala_jobs: dict[str, MapalaJob]`
- MapalaJob stocke : template_df, source_df, result_df, fichiers uploadés, config
- TTL : même durée que les jobs Tablerreur

## Tâche 3 — UI web : navigation par onglets

Transforme l'UI pour avoir deux onglets principaux :

### Dans index.html :
1. Ajoute une barre de navigation globale en haut (au-dessus de la barre d'étapes) :
```html
<nav class="app-tabs">
  <button id="tab-tablerreur" class="app-tab active">🔍 Tablerreur</button>
  <button id="tab-mapala" class="app-tab">🗺️ Mapala</button>
</nav>
```

2. Encapsule tout le contenu actuel de Tablerreur dans un `<div id="app-tablerreur">...</div>`

3. Ajoute un `<div id="app-mapala" hidden>` avec la structure Mapala (voir Tâche 4)

### Logique (app.js) :
- `switchApp(appName)` : affiche/masque les divs, met à jour la classe active sur les onglets
- L'état de chaque app est indépendant (changer d'onglet ne réinitialise pas l'autre)

### CSS :
- `.app-tabs` : flexbox, fond légèrement différent de la barre d'étapes, padding
- `.app-tab` : bouton style onglet, border-bottom quand actif
- Couleur d'accent Mapala : #059669 (vert émeraude) vs #2563eb (bleu) pour Tablerreur
- L'onglet actif a une bordure inférieure colorée de la couleur de l'app

## Tâche 4 — UI Mapala : interface de mapping

Crée le contenu du div #app-mapala avec 4 étapes :

### Étape 1 — Upload
```html
<div id="mapala-step-upload">
  <h2>1. Chargez vos fichiers</h2>
  <div class="mapala-upload-zone">
    <div>
      <label>Fichier template (modèle cible)</label>
      <input type="file" id="mapala-template-file" accept=".xlsx,.xls,.ods,.csv">
      <select id="mapala-template-sheet"></select>
    </div>
    <div>
      <label>Fichier source (données à mapper)</label>
      <input type="file" id="mapala-source-file" accept=".xlsx,.xls,.ods,.csv">
      <select id="mapala-source-sheet"></select>
    </div>
  </div>
  <button id="mapala-btn-preview">Charger l'aperçu →</button>
</div>
```

### Étape 2 — Aperçu + Mapping
La partie la plus importante. Deux tableaux côte à côte (ou haut/bas) avec un panneau de mapping.

```html
<div id="mapala-step-mapping">
  <h2>2. Mappez les colonnes</h2>
  
  <!-- Aperçu des deux fichiers -->
  <div class="mapala-preview-split">
    <div class="mapala-preview-panel">
      <h3>Template (cible)</h3>
      <table id="mapala-template-table">...</table>
    </div>
    <div class="mapala-preview-panel">
      <h3>Source (données)</h3>
      <table id="mapala-source-table">...</table>
    </div>
  </div>

  <!-- Configuration du mapping -->
  <div id="mapala-mapping-config">
    <h3>Configuration du mapping</h3>
    <!-- Une ligne par colonne template -->
    <div class="mapala-mapping-row" data-template-col="titre">
      <span class="mapala-col-name">titre</span>
      <span>←</span>
      <select class="mapala-source-select">
        <option value="">— Non mappé —</option>
        <option value="Titre de l'oeuvre">Titre de l'oeuvre</option>
        ...
      </select>
      <!-- Bouton pour mode concat (multi-colonnes) -->
      <button class="mapala-btn-concat">+</button>
      <!-- Ou valeur fixe -->
      <input type="text" class="mapala-fixed-value" placeholder="Valeur fixe (optionnel)">
    </div>
    ...
  </div>

  <button id="mapala-btn-build">Construire le fichier →</button>
</div>
```

### Étape 3 — Résultat
```html
<div id="mapala-step-result">
  <h2>3. Résultat</h2>
  <p id="mapala-result-info">150 lignes mappées, 4 colonnes.</p>
  <table id="mapala-result-table">...</table>
  <div class="mapala-result-actions">
    <button id="mapala-btn-download">💾 Télécharger</button>
    <button id="mapala-btn-validate">🔍 Valider avec Tablerreur →</button>
  </div>
</div>
```

Le bouton "Valider avec Tablerreur" :
1. Appelle POST /api/mapala/jobs/{id}/validate
2. Récupère le tablerreur_job_id
3. Switch sur l'onglet Tablerreur
4. Charge le job Tablerreur (passe directement à l'étape Configurer)

### Logique JS (dans un nouveau fichier mapala.js ou dans app.js) :

Fonctions principales :
- `mapalaUpload()` : upload les deux fichiers, remplit les selects de feuilles
- `mapalaLoadPreview()` : fetch POST /preview, affiche les deux tableaux + génère les lignes de mapping
- `mapalaBuild()` : collecte la config de mapping, POST /build, affiche le résultat
- `mapalaDownload()` : déclenche le téléchargement
- `mapalaValidate()` : POST /validate, switch onglet

### Support du mode concat (multi-colonnes) :
Quand l'utilisateur clique "+", la ligne de mapping passe en mode concat :
- Affiche un second select (colonne source 2)
- Champ séparateur (défaut " ")
- Possibilité d'ajouter des préfixes
- Bouton "−" pour revenir au mode simple

## Tâche 5 — CSS Mapala

- `.mapala-preview-split` : flexbox, deux panneaux 50/50 (ou colonne sur mobile)
- `.mapala-preview-panel` : overflow-x auto, max-height 300px
- `.mapala-mapping-row` : flexbox, aligné verticalement, gap, fond alterné
- `.mapala-col-name` : font-weight bold, largeur fixe 150px
- `.mapala-source-select` : largeur 200px
- Couleur d'accent verte (#059669) pour les boutons et éléments actifs Mapala
- Mode sombre supporté (réutilise les variables CSS existantes)

## Tâche 6 — Fichier JS séparé (optionnel mais recommandé)

Si app.js devient trop gros (>1000 lignes), crée web/static/mapala.js :
- Contient toute la logique Mapala
- Chargé via <script> dans index.html après app.js
- Communique avec app.js via state global et fonctions partagées (switchApp, showToast, etc.)

## Tâche 7 — Hidden imports pour le sidecar

Si odfpy est utilisé par Mapala pour les fichiers ODS, vérifie qu'il est dans les hidden-imports de build_sidecar.py.
Ajoute aussi les modules Mapala :
```
--hidden-import spreadsheet_qa.core.mapala
--hidden-import spreadsheet_qa.core.mapala.config
--hidden-import spreadsheet_qa.core.mapala.io_excel
--hidden-import spreadsheet_qa.core.mapala.template_builder
```

## Règles
- Textes visibles : français
- Code : anglais
- Ne modifie PAS le core Tablerreur (core/rules/, core/models.py, etc.)
- Ne modifie PAS ui/ (legacy Qt)
- Les endpoints Mapala sont préfixés /api/mapala/
- pytest doit passer après chaque tâche
- Le mode sombre doit fonctionner pour l'UI Mapala
```
