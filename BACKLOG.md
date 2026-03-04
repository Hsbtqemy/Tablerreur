# Backlog Tablerreur â€” Validation par colonne & UX

> DerniÃ¨re mise Ã  jour : mars 2026
> Statuts : âœ… Fait | ðŸ”œ Prochaine itÃ©ration | ðŸ“‹ Backlog | ðŸ”® Long terme

---

## Ã‰valuation et prioritÃ©s (vue consolidÃ©e)

AprÃ¨s Ã©valuation de la **faisabilitÃ©** (technique, dÃ©pendances, effort) et **priorisation**, voici le classement des idÃ©es du backlog.

### LÃ©gende faisabilitÃ©

| Symbole | Signification |
|--------|----------------|
| ðŸŸ¢ | Faisable sans blocant â€” stack actuelle suffisante, effort raisonnable |
| ðŸŸ¡ | Faisable avec prÃ©alable ou effort moyen â€” doc API, refactor lÃ©ger, ou UX non triviale |
| ðŸ”´ | Ã€ clarifier â€” dÃ©pend d'un acteur externe (API, schÃ©ma) ou pÃ©rimÃ¨tre Ã  dÃ©finir |
| ðŸ”® | Long terme â€” complexitÃ© forte ou prioritÃ© mÃ©tier faible |

### PrioritÃ© globale (ordre recommandÃ©)

| PrioritÃ© | ThÃ¨me | IdÃ©es | FaisabilitÃ© |
|----------|--------|--------|-------------|
| **P0 â€” Haute** | Distribution | Menu Aide â†’ URL releases | ðŸŸ¢ |
| **P1 â€” Moyenne** | Curation & Ã©dition | Ã‰tape Curation, Ã©dition in-place, persistance, export aprÃ¨s curation, curation ciblÃ©e (issues â†’ cellule) | ðŸŸ¢ |
| **P1** | NAKALA â€” sÃ©lection | Choisir un sous-ensemble dans le vocabulaire chargÃ© (liste Ã  cocher ou select multiple), cohÃ©rence rÃ¨gles NAKALA | ðŸŸ¢ |
| **P1** | UX avancÃ©e | VisibilitÃ© des caractÃ¨res invisibles/espaces dans cellules en erreur, intÃ©gration Mapala | ðŸŸ¢ / ðŸŸ¡ |
| **P2** | NAKALA â€” template API | Doc/dÃ©couverte API NAKALA (prÃ©alable), puis gÃ©nÃ©ration template Â« NAKALA pur Â» | ðŸ”´ â†’ ðŸŸ¡ (aprÃ¨s doc) |
| **P2** | Presets & rÃ¨gles | Presets ISBN, Date FR, BCP 47, Pays ISO, Lat/Long ; normalisation casse (suggestion) | ðŸŸ¢ |
| **P2** | Curation avancÃ©e | Historique / undo dans l'Ã©tape curation (rÃ©utilisation CommandHistory si pertinent) | ðŸŸ¢ |
| **P2** | NAKALA dÃ©tail | Option Â« une seule valeur Â», dÃ©verrouiller / personnaliser aprÃ¨s chargement | ðŸŸ¢ |
| **P3 â€” Basse** | Presets secondaires | Email, URL, Handle, slug, intervalle annÃ©es, code postal FR ; coordonnÃ©es east/north (parsing structurÃ©) | ðŸŸ¢ / ðŸ”® |
| **Long terme** | Enrichissement | Auto-update Tauri, constructeur visuel regex, dÃ©tection automatique du format | ðŸŸ¡ / ðŸ”® |

### FaisabilitÃ© par bloc (rÃ©sumÃ©)

- **Briques de base (Â§1)** : Valeurs rÃ©pÃ©tÃ©es autorisÃ©es = ðŸŸ¢ (label UI uniquement). Reste 1 item.
- **Presets (Â§2)** : Actuels tous âœ…. Restants ðŸŸ¢ sauf coordonnÃ©es structurÃ©es ðŸ”®.
- **CohÃ©rence (Â§4)** : `similar_values` âœ… exposÃ© dans l'UI ; vocab NAKALA âœ….
- **NAKALA sÃ©lection (Â§7A)** : ðŸŸ¢ â€” uniquement UI (checkboxes/select), `allowed_values` dÃ©jÃ  gÃ©rÃ©.
- **NAKALA template (Â§7B)** : ðŸ”´ tant que l'API NAKALA n'a pas Ã©tÃ© vÃ©rifiÃ©e ; ðŸŸ¡ aprÃ¨s doc.
- **Curation (Â§8)** : ðŸŸ¢ â€” endpoints et Ã©tat job existants ; CommandHistory rÃ©utilisable.
- **Infra (Â§6)** : Signing macOS hors pÃ©rimÃ¨tre (compte Apple payant non prÃ©vu) ; onedir âœ…, Dockerfile âœ…, limites upload âœ….

---

## 1. Briques de base (contrÃ´les par colonne)

### A. PrÃ©sence et cardinalitÃ©

| FonctionnalitÃ© | Statut | DÃ©tail |
|---|---|---|
| Valeurs uniques | âœ… | `generic.unique_column` â€” exposÃ© dans UI web |
| Pseudo-manquants (NA, N/A, null, -â€¦) | âœ… | `generic.pseudo_missing` â€” tokens configurables |
| Obligatoire / facultatif par colonne | âœ… | `generic.required` â€” signale les cellules vides si `required: true` |
| Valeurs rÃ©pÃ©tÃ©es autorisÃ©es (inverse d'unique) | ðŸ“‹ | Variante UX de `unique` â€” pas de nouvelle rÃ¨gle, juste un label inversÃ© dans l'UI |

### B. Forme gÃ©nÃ©rale

| FonctionnalitÃ© | Statut | DÃ©tail |
|---|---|---|
| Longueur min/max | âœ… | `generic.length` â€” exposÃ© dans UI web |
| Multiligne autorisÃ© | âœ… | `generic.unexpected_multiline` â€” exposÃ© dans UI web |
| Nettoyages (trim, espaces, NBSP, invisibles, Unicode, retours ligne) | âœ… | Correctifs typiques, Ã©tape 3 du web |

### C. Jeu de caractÃ¨res & casse

| FonctionnalitÃ© | Statut | DÃ©tail |
|---|---|---|
| Uniquement chiffres | âœ… | Couvert par preset regex `positive_int` ou `content_type: integer` |
| AlphanumÃ©rique | âœ… | Couvert par preset regex `alphanum` |
| Lettres uniquement (+ accents, tirets, apostrophes) | âœ… | Couvert par preset regex `letters_only` |
| Interdire certains caractÃ¨res | âœ… | `generic.forbidden_chars` â€” config : liste de caractÃ¨res interdits |
| Casse imposÃ©e (UPPER / lower / Title) | âœ… | `generic.case` â€” config : `case: upper\|lower\|title` |

---

## 2. Presets de format (catalogue regex)

### Actuellement disponibles

| Preset | Statut | Regex |
|---|---|---|
| AnnÃ©e (YYYY) | âœ… | `^\d{4}$` |
| Oui / Non | âœ… | `(?i)^(oui\|non\|â€¦)$` â€” mapping personnalisable |
| AlphanumÃ©rique | âœ… | `^[A-Za-z0-9]+$` |
| Lettres uniquement | âœ… | `^[A-Za-zÃ€-Ã¿\s\-']+$` |
| Entier positif | âœ… | `^\d+$` |
| PersonnalisÃ© (avancÃ©) | âœ… | Champ regex libre |
| DOI | âœ… | `^10\.\d{4,9}/[^\s]+$` |
| ORCID | âœ… | `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` |
| ARK | âœ… | `^ark:/\d{5}/.+$` |
| ISSN | âœ… | `^\d{4}-\d{3}[\dX]$` |
| Date W3C-DTF | âœ… | `^\d{4}(-\d{2}(-\d{2})?)?$` |
| Date ISO stricte (YYYY-MM-DD) | âœ… | `^\d{4}-\d{2}-\d{2}$` |
| Langue ISO 639 (fr, en, deâ€¦) | âœ… | `(?i)^[a-z]{2,3}$` |

### Ã€ ajouter â€” Identifiants & liens

| Preset | Statut | Regex / logique | PrioritÃ© |
|---|---|---|---|
| Email (comme preset, pas seulement content_type) | ðŸ“‹ | `^[^@\s]+@[^@\s]+\.[^@\s]+$` | Basse |
| URL (comme preset) | ðŸ“‹ | `https?://\S+` | Basse |
| ISBN-13 | ðŸ“‹ | `^97[89]\d{10}$` (sans tirets) | Moyenne |
| ISBN-10 | ðŸ“‹ | `^\d{9}[\dX]$` | Moyenne |
| Handle | ðŸ“‹ | `^\d+(\.\d+)*/.+$` | Basse |
| Identifiant interne (slug) | ðŸ“‹ | `^[a-z0-9\-]+$` | Basse |

### Ã€ ajouter â€” Dates & temps

| Preset | Statut | Regex / logique | PrioritÃ© |
|---|---|---|---|
| Date FR (JJ/MM/AAAA) | ðŸ“‹ | `^\d{2}/\d{2}/\d{4}$` + bornes | Moyenne |
| Intervalle d'annÃ©es (YYYY-YYYY) | ðŸ“‹ | `^\d{4}-\d{4}$` | Basse |

### Ã€ ajouter â€” Codes & rÃ©fÃ©rentiels

| Preset | Statut | Regex / logique | PrioritÃ© |
|---|---|---|---|
| Langue BCP 47 (fr-FR, en-GB, ocâ€¦) | ðŸ“‹ | `^[a-z]{2,3}(-[A-Z]{2})?$` | Moyenne |
| Pays ISO 3166-1 alpha-2 (FR, DEâ€¦) | ðŸ“‹ | Liste fermÃ©e 2 lettres majuscules | Moyenne |
| Code postal FR | ðŸ“‹ | `^\d{5}$` | Basse |

### Ã€ ajouter â€” Nombres & mesures

| Preset | Statut | DÃ©tail | PrioritÃ© |
|---|---|---|---|
| Latitude | ðŸ“‹ | DÃ©cimal entre -90 et 90 | Moyenne |
| Longitude | ðŸ“‹ | DÃ©cimal entre -180 et 180 | Moyenne |
| CoordonnÃ©es "east=â€¦; north=â€¦" | ðŸ”® | Parsing structurÃ© | Basse |

---

## 3. ContrÃ´les "valeurs multiples dans une cellule"

| FonctionnalitÃ© | Statut | DÃ©tail | PrioritÃ© |
|---|---|---|---|
| Liste simple (sÃ©parateur configurable) : split + trim items | âœ… | `generic.list_items` â€” config : `list_separator` |  |
| Liste contrÃ´lÃ©e : chaque item dans allowed_values | âœ… | Extension de `generic.allowed_values` pour mode liste |  |
| Items uniques dans la liste | âœ… | Option `list_unique: true` |  |
| Nombre min / max d'items | âœ… | Options `list_min_items`, `list_max_items` |  |
| Interdire les items vides | âœ… | Option `list_no_empty: true` (dÃ©faut) |  |
| Paires clÃ©=valeur | ðŸ”® | Parsing structurÃ© | Basse |

---

## 4. CohÃ©rence interne (au-delÃ  du regex)

| FonctionnalitÃ© | Statut | DÃ©tail | PrioritÃ© |
|---|---|---|---|
| Valeurs rares (suspicion de faute de saisie) | âœ… | `generic.rare_values` â€” seuil et minimum configurables |  |
| Valeurs trÃ¨s proches (typo probable, similaritÃ©) | âœ… | `generic.similar_values` â€” via rapidfuzz, exposÃ© dans l'UI web (checkbox + seuil) |  |
| Normalisation suggÃ©rÃ©e (FR vs Fr vs fr) | ðŸ“‹ | Extension de `generic.case` â€” mode suggestion | Moyenne |
| Dictionnaire contrÃ´lÃ© distant (vocab NAKALA) | âœ… | `nakala_api.py` + rÃ¨gles `nakala.deposit_type` / `nakala.license` / `nakala.language` ; chargement vocabulaire dans l'UI via endpoint `/api/nakala/vocabulary/{vocab_name}` | SÃ©lection sous-ensemble en backlog |

---

## 5. UX de la configuration par colonne

| FonctionnalitÃ© | Statut | DÃ©tail |
|---|---|---|
| Panneau inline au clic sur en-tÃªte | âœ… | ImplÃ©mentÃ© dans l'Ã©tape "Configurer" |
| Dropdown "Format attendu" (presets) | âœ… | 13 presets en 5 groupes (optgroup) |
| Texte d'aide contextuel par preset | âœ… | Exemples valides/invalides |
| Mode regex avancÃ© | âœ… | Champ libre cachÃ© par dÃ©faut |
| PrÃ©-remplissage depuis template | âœ… | Template â†’ config initiale, Ã©ditable |
| Oui/Non avec mapping personnalisable | âœ… | Config : `yes_no_true_values`, `yes_no_false_values` |
| Mode "SÃ©lection" (liste fermÃ©e non Ã©ditable) | âœ… | `allowed_values_locked: true` â€” textarea en lecture seule |
| CatÃ©gorisation des presets (groupes dans le dropdown) | âœ… | 5 groupes : GÃ©nÃ©raux, Identifiants, Dates, Codes, AvancÃ© |
| AperÃ§u temps rÃ©el (3 OK / 3 rejetÃ©es) | âœ… | Endpoint `POST /preview-rule`, debounce 300ms |
| Badges sur colonnes configurÃ©es | âœ… | Point vert `â—` sur `<th>`, tooltip rÃ©sumÃ© |
| RÃ©sumÃ© de configuration avant Ã©tape suivante | âœ… | Tableau rÃ©capitulatif + boutons Modifier / Continuer |
| Surlignage des cellules en erreur dans l'aperÃ§u | âœ… | Endpoint `GET /preview-issues`, classes `cell-error/warning/suspicion` |
| Import de template YAML depuis l'UI | âœ… | Upload `.yaml` Ã  l'Ã©tape Upload et Ã  l'Ã©tape Configurer ; endpoint `POST /import-template` |
| Export de template YAML depuis l'UI | âœ… | TÃ©lÃ©charger la config courante en `.yaml` ; endpoint `GET /export-template` |
| Import de vocabulaire personnalisÃ© | âœ… | Upload `.yaml` de vocabulaire ; endpoint `POST /import-vocabulary` |
| SÃ©lecteur vocabulaire NAKALA dans le panneau | âœ… | Bouton Â« Charger vocabulaire NAKALA Â» dans le panneau de config colonne |
| DÃ©tection valeurs similaires | âœ… | Checkbox + seuil dans le panneau de config colonne ; `generic.similar_values` via rapidfuzz |
| Enrichir le menu Â« Type de contenu Â» | ðŸ“‹ | Aujourd'hui seulement 5 types (entier, dÃ©cimal, date, email, URL). Voir ciâ€‘dessous les types manquants. | Moyenne |
| Restreindre les formats attendus selon le type choisi | ðŸ“‹ | Filtrer le dropdown Â« Format attendu Â» selon le type sÃ©lectionnÃ© (ex. type Date â†’ AnnÃ©e, W3C-DTF, ISO). Voir `docs/type-format-mapping.md`. | Moyenne |
| Un seul type Â« Nombre Â» avec formats (entier, dÃ©cimal, etc.) | ðŸ“‹ | Fusionner Â« Nombre entier Â» et Â« Nombre dÃ©cimal Â» en un type **Nombre** avec formats. Voir `docs/type-format-mapping.md`. | Moyenne |
| Constructeur visuel de regex | ðŸ”® | Interface drag-and-drop de blocs | Long terme |
| DÃ©tection automatique du format probable | ðŸ”® | Heuristique sur les donnÃ©es chargÃ©es | Long terme |

#### Types de contenu manquants (candidats)

| Type proposÃ© | Existant en format ? | FaisabilitÃ© | PrioritÃ© |
|-------------|----------------------|-------------|----------|
| **Texte** (`text`) | â€” | Aucun type Â« texte Â» actuellement ; formats `alphanum`, `letters_only`, `yes_no` sans type dÃ©diÃ©. Voir `docs/type-format-mapping.md`. | Moyenne |
| AnnÃ©e (YYYY) | âœ… `year` | Pas de nouveau type : une annÃ©e est une date partielle. Garder Type = Date + Format = AnnÃ©e. DÃ©jÃ  couvert. | â€” |
| Oui / Non (boolÃ©en) | âœ… `yes_no` | Peut rester en format uniquement | Basse |
| Code langue (ISO 639) | âœ… `lang_iso639` | Utile pour NAKALA | Moyenne |
| **Identifiant** (DOI, ORCID, ARK, ISSNâ€¦) | âœ… presets dÃ©diÃ©s | Un seul type **Identifiant** ; formats = DOI, ORCID, ARK, ISSN (puis ISBN, Handle). Voir `docs/type-format-mapping.md`. | Moyenne |
| **Adresse** (e-mail, URL) | âœ… types actuels | Fusionner en un type **Adresse** ; formats = E-mail, URL. Voir `docs/type-format-mapping.md`. | Moyenne |
| **Type NAKALA** | âœ… rÃ¨gles + API | Un seul type **NAKALA** ; formats = Type de ressource, Licence, Langue, Date crÃ©Ã©e, CrÃ©ateur. Voir `docs/type-format-mapping.md`. | Basse |
| Texte court / Texte long | â€” | Variante du type Texte ; longueur min/max + multiligne. | Basse |
| Autres types envisagÃ©s | â€” | **Langue** (ISO 639, BCP 47), **BoolÃ©en** (Oui/Non), **Pays** (ISO 3166), **CoordonnÃ©es** (lat/long), **URI** (gÃ©nÃ©rique). Voir `docs/type-format-mapping.md` Â§1c. | Basse Ã  Moyenne |

---

## 6. Infrastructure & distribution

| FonctionnalitÃ© | Statut | DÃ©tail | PrioritÃ© |
|---|---|---|---|
| Launcher standalone (`python -m spreadsheet_qa.web`) | âœ… | Port auto + navigateur | |
| Endpoint `/health` | âœ… | Retourne `{"status": "ok", "version": "..."}` | |
| Tauri â€” init projet | âœ… | `src-tauri/`, Cargo.toml, tauri.conf.json | |
| Tauri â€” sidecar Python | âœ… | PyInstaller via `build_sidecar.py` | |
| Tauri â€” sidecar onedir (dÃ©marrage ~1,4s) | âœ… | Mode `--onedir` PyInstaller, dossier `_internal/`, plus d'extraction au lancement | |
| Tauri â€” splash screen FR | âœ… | HTML embarquÃ© en data URI (`include_str!`), adaptÃ© mode sombre | |
| Tauri â€” menu natif (Fichier, Aide) | âœ… | Fichier â†’ Quitter ; Aide â†’ VÃ©rifier MÃ J | |
| Tauri â€” health check avant navigation | âœ… | Poll TCP toutes les 200ms, port 8400â€“8500 | |
| Tauri â€” icÃ´ne `.icns` / `.ico` / PNG | âœ… | Lettre T blanche, fond bleu #2563eb | |
| Tauri â€” `.dmg` debug (non signÃ©) | âœ… | GÃ©nÃ©rÃ© via `npm run tauri build` | |
| DÃ©ploiement online (Dockerfile) | âœ… | Dockerfile multi-stage (sans PySide6) + docker-compose.yml | |
| Limites upload (taille, types MIME) | âœ… | `TABLERREUR_MAX_UPLOAD_MB`, validation extension/MIME | |
| CORS configurable | âœ… | `TABLERREUR_CORS_ORIGINS` | |
| Variable `TABLERREUR_ENV` (dev/prod) | âœ… | ContrÃ´le comportements dev vs prod | |
| Tauri â€” menu Aide cÃ¢blÃ© (ouvre URL releases) | ðŸ“‹ | Item prÃ©sent, action non implÃ©mentÃ©e | Moyenne |
| Tauri â€” signing macOS (certificat Apple Developer) | â€” | Hors pÃ©rimÃ¨tre (compte Apple 99 â‚¬/an non prÃ©vu) ; .dmg reste non signÃ© | â€” |
| Tauri â€” auto-update | ðŸ”® | Plugin Tauri updater | Long terme |

---

## Ordre recommandÃ© (prochaines sessions)

1. **Haute prioritÃ© â€” Distribution**
   - Menu Aide â†’ ouvrir URL GitHub releases

2. **Moyenne prioritÃ© â€” Fonctionnel**
   - Ã‰tape Curation (Ã©dition in-place des cellules, persistance, export)
   - SÃ©lection d'un sous-ensemble dans le vocabulaire NAKALA chargÃ©
   - VisibilitÃ© des caractÃ¨res invisibles/espaces dans les cellules en erreur

3. **Enrichissement**
   - Presets supplÃ©mentaires (ISBN, Date FR, BCP 47, Pays ISO, Lat/Long)
   - NAKALA : template depuis l'API, valeurs spÃ©ciales (Inconnue, Anonyme)
   - Auto-update Tauri
   - DÃ©tection automatique de format
   - Constructeur visuel de regex

---

## 7. Vocabulaires NAKALA â€” sÃ©lection et templates

### A. SÃ©lection dans le vocabulaire chargÃ©

Actuellement : Â« Charger le vocabulaire NAKALA Â» remplit *toute* la liste des valeurs autorisÃ©es et la verrouille ; la colonne accepte n'importe quelle valeur du vocabulaire.

| IdÃ©e | Statut | DÃ©tail | PrioritÃ© |
|------|--------|--------|----------|
| Choisir un sous-ensemble dans le vocabulaire chargÃ© | ðŸ“‹ | AprÃ¨s chargement, permettre de sÃ©lectionner une ou plusieurs valeurs (ex. une seule licence, ou quelques types de ressource) au lieu d'accepter l'intÃ©gralitÃ© du vocabulaire. | Moyenne |
| UI : liste Ã  cocher aprÃ¨s chargement | ðŸ“‹ | Afficher les valeurs du vocabulaire en cases Ã  cocher ; l'utilisateur coche celles qu'il veut autoriser ; `allowed_values` = sÃ©lection. | Moyenne |
| UI : select multiple | ðŸ“‹ | Alternative : `<select multiple>` pour choisir les valeurs ; mÃªme rÃ©sultat (liste filtrÃ©e â†’ `allowed_values`). | Moyenne |
| Option Â« une seule valeur Â» (liste dÃ©roulante) | ðŸ“‹ | Cas particulier : une seule valeur sÃ©lectionnable (ex. Â« cette colonne = CC-BY-4.0 Â») ; `allowed_values` Ã  un Ã©lÃ©ment. | Basse |
| DÃ©verrouiller / personnaliser aprÃ¨s chargement | ðŸ“‹ | Bouton Â« Personnaliser Â» pour dÃ©verrouiller le textarea et Ã©diter la liste tout en gardant la trace `nakala_vocabulary`. | Basse |
| CohÃ©rence rÃ¨gles NAKALA | ðŸ“‹ | Si l'utilisateur ne garde qu'un sous-ensemble : les rÃ¨gles `nakala.deposit_type` / `nakala.license` / `nakala.language` pourraient soit utiliser la liste configurÃ©e (allowed_values) au lieu du vocabulaire complet, soit rester sur le vocabulaire complet (comportement Ã  trancher). | Moyenne |

### B. Template depuis l'API NAKALA

CrÃ©er un template de validation (colonnes + rÃ¨gles) uniquement Ã  partir de ce que l'API NAKALA expose (vocabulaires, champs requis/recommandÃ©s), sans repartir d'un YAML builtin.

| IdÃ©e | Statut | DÃ©tail | PrioritÃ© |
|------|--------|--------|----------|
| DÃ©couverte des champs NAKALA via l'API | ðŸ“‹ | Si l'API NAKALA expose une liste de champs (requis / recommandÃ©s / optionnels) ou un schÃ©ma, l'utiliser pour gÃ©nÃ©rer la structure du template. | Ã€ prÃ©ciser |
| GÃ©nÃ©ration de template Â« NAKALA pur Â» | ðŸ“‹ | Endpoint ou flux UI : Â« CrÃ©er un template depuis NAKALA Â» â†’ appel API â†’ template YAML ou config en mÃ©moire. | Moyenne |
| Template = colonnes + vocabulaires branchÃ©s | ðŸ“‹ | Le template gÃ©nÃ©rÃ© attache les vocabulaires aux colonnes correspondantes ; l'utilisateur peut ensuite appliquer la sÃ©lection (cf. Â§ A). | Moyenne |
| Documentation / dÃ©couverte API | ðŸ“‹ | VÃ©rifier la doc officielle NAKALA (champs, vocabulaires, Ã©ventuels endpoints de schÃ©ma). RÃ©fÃ©rence : `docs/nakala-validation-formats.md`. | Haute (avant implÃ©mentation) |
| Appliquer NAKALA (RÃ©fÃ©rence / Ã‰tendu) en overlay Ã  l'upload | ðŸ“‹ | Corriger : envoyer generic_id=generic_default + overlay_id=nakala_baseline|nakala_extended pour que la config = base gÃ©nÃ©rique + overlay NAKALA. | Moyenne |
| Transformation libellÃ© â†’ URI (COAR, etc.) | ðŸ“‹ | Correctif Â« Remplacer par l'URI COAR Â» quand la valeur est un libellÃ© reconnu ; ou mapping libellÃ© â†’ URI Ã  l'import/export. | Moyenne |
| Appliquer le type selon le champ dcterms/nakala souhaitÃ© | ðŸ“‹ | En configuration de colonne : indiquer quel champ dcterms/nakala est ciblÃ© ; l'interface applique vocabulaire et rÃ¨gle adaptÃ©s. | Moyenne |
| Afficher les valeurs NAKALA en libellÃ©s avec stockage URI | ðŸ“‹ | Proposer une liste en libellÃ©s (image, video, sonâ€¦) avec stockage/validation en URI. **Ã€ vÃ©rifier dans la pratique** â€” ne pas implÃ©menter de suite. | Ã€ vÃ©rifier |
| Champs dcterms manquants + schÃ©ma d'export NAKALA | ðŸ“‹ | IntÃ©grer dcterms:creator, dcterms:contributor, dcterms:publisher, dcterms:rightsHolder, etc. Voir `docs/nakala.md`. | Moyenne |
| Validation propriÃ©tÃ©s/encodages via API NAKALA | ðŸ“‹ | Utiliser `GET /vocabularies/properties` et `GET /vocabularies/metadatatypes` pour valider propriÃ©tÃ©s et encodages. Voir `docs/nakala-validation-formats.md`. | Moyenne |
| Relations DataCite (RelationType) | ðŸ“‹ | Valider que le type de relation appartient Ã  la liste fermÃ©e DataCite. Voir `docs/nakala-validation-formats.md` Â§6. | Moyenne |
| Encodages structurÃ©s dcterms (Box, Point, Period) | ðŸ“‹ | Valider les formats dcterms:Box, dcterms:Point, dcterms:Period. Voir `docs/nakala-validation-formats.md` Â§5. | Basse |
| Collections NAKALA (statut, titre) | ðŸ“‹ | Support spÃ©cifique collections : statut privÃ©/public via `GET /vocabularies/collectionStatuses`. Voir `docs/nakala-validation-formats.md` Â§7. | Basse |
| Messages d'erreur NAKALA en franÃ§ais | ðŸ“‹ | Les rÃ¨gles `nakala.*` renvoient des messages en anglais. Traduire pour l'UI web et les exports. Voir `docs/nakala-validation-formats.md` Â§9.1. | Moyenne |
| Valeurs spÃ©ciales NAKALA : Â« Inconnue Â» (date), Â« Anonyme Â» (crÃ©ateur) | ðŸ“‹ | Accepter Â« Inconnue Â» pour `nakala:created` et Â« Anonyme Â» pour `nakala:creator`. Voir `docs/nakala-validation-formats.md` Â§9.2. | Moyenne |

### Ordre suggÃ©rÃ© (NAKALA)

1. **Documentation** : confirmer ce que l'API NAKALA expose (champs, schÃ©ma, vocabulaires). RÃ©fÃ©rence : `docs/nakala-validation-formats.md`.
2. **SÃ©lection** : UI pour choisir un sous-ensemble dans le vocabulaire chargÃ©, puis cohÃ©rence avec les rÃ¨gles NAKALA.
3. **Template depuis l'API** : gÃ©nÃ©ration d'un template (colonnes + rÃ¨gles) Ã  partir des donnÃ©es NAKALA disponibles.

---

## 8. Ã‰tape curation â€” Ã©dition manuelle des cellules

PossibilitÃ© pour l'utilisateur de modifier directement certaines cellules dans l'interface (correction manuelle, curation), dans une Ã©tape dÃ©diÃ©e ou intÃ©grÃ©e au flux actuel.

| IdÃ©e | Statut | DÃ©tail | PrioritÃ© |
|------|--------|--------|----------|
| Ã‰tape Â« Curation Â» dans le workflow | ðŸ“‹ | Ajouter une Ã©tape (ex. aprÃ¨s Validation ou Correctifs) oÃ¹ l'utilisateur peut Ã©diter les valeurs du tableau : clic sur une cellule â†’ Ã©dition in-place, sauvegarde dans le job. | Moyenne |
| Ã‰dition in-place dans le tableau d'aperÃ§u | ðŸ“‹ | Rendre les cellules du tableau d'aperÃ§u Ã©ditables : focus â†’ saisie â†’ validation â†’ mise Ã  jour du DataFrame cÃ´tÃ© backend. | Moyenne |
| Curation ciblÃ©e (cellules en erreur) | ðŸ“‹ | Proposer d'Ã©diter en prioritÃ© les cellules signalÃ©es par la validation (liste des issues â†’ clic â†’ ouvrir la cellule en Ã©dition avec suggestion si disponible). | Moyenne |
| Persistance des modifications | ðŸ“‹ | Les changements de curation doivent Ãªtre renvoyÃ©s au backend (endpoint type PATCH/PUT sur les donnÃ©es du job), re-validation optionnelle aprÃ¨s Ã©dition. | Moyenne |
| Historique / annuler une modification | ðŸ“‹ | Undo/redo dans l'Ã©tape curation (peut s'appuyer sur `CommandHistory` / `ApplyCellFixCommand` cÃ´tÃ© core). | Basse |
| Export aprÃ¨s curation | ðŸ“‹ | S'assurer que l'export (CSV, XLSX) reflÃ¨te les valeurs Ã©ditÃ©es lors de la curation. | Moyenne |

---

## 9. UX avancÃ©e â€” nouveaux items

| IdÃ©e | Statut | DÃ©tail | PrioritÃ© |
|------|--------|--------|----------|
| VisibilitÃ© des caractÃ¨res invisibles/espaces | ðŸ“‹ | Dans les cellules signalÃ©es par `generic.hygiene.invisible_chars` ou `generic.hygiene.leading_trailing_space`, afficher visuellement les caractÃ¨res problÃ©matiques (ex. pilcrow Â¶, point mÃ©dian Â·, surlignage) pour que l'utilisateur comprenne l'erreur. | Moyenne |
| IntÃ©gration Mapala | ðŸ“‹ | IntÃ©gration avec Mapala (mapping de tableur) dans le mÃªme Tauri ou en fenÃªtre liÃ©e. PÃ©rimÃ¨tre Ã  dÃ©finir. | Ã€ prÃ©ciser |

---

## 10. Decisions figees - Correctifs (mars 2026)

Decisions validees avant passage a l'onglet suivant :

- Statuts UX retenus : `OPEN` et `IGNORED` uniquement.
- `EXCEPTED` : retire/masque de l'interface utilisateur.
- Pas de justification obligatoire pour ignorer une anomalie.

## 11. Decision figee - Export depuis l'etape Correctifs (mars 2026)

Decision validee :

- Ajouter un **export de travail** directement dans l'etape `Correctifs` (etape 4),
  afin de sortir un tableur annote avec les erreurs marquees, avant la validation finale.

Position technique :

- Le branchement backend est **possible** avec la stack actuelle (job en memoire + liste d'issues).
- Ce n'est **pas encore implemente** : la maquette UX est prete, il faut brancher les endpoints.

Perimetre backend minimal a prevoir :

- `POST /api/jobs/{job_id}/exports/annotated`
  : genere un tableur annote (xlsx/csv/ods/json selon format demande).
- `POST /api/jobs/{job_id}/exports/issues-report`
  : genere un rapport d'anomalies (json/csv/pdf selon format demande).
- Options supportees : perimetre (`all|issues|blocking|touched`), marquage visuel, colonne statut, only_open.

Critere d'acceptation :

- Depuis l'etape `Correctifs`, l'utilisateur peut exporter un fichier de travail
  contenant les erreurs marquees et/ou un rapport des anomalies, sans devoir terminer tout le workflow.
- Passage Correctifs -> Valider : autorise uniquement s'il ne reste plus d'anomalie `ERROR` en `OPEN`.
- Une cellule deja modifiee reste re-editable.
- La liste des anomalies est re-calculee a la `Re-valider` (source de verite finale).
- En vue Resultats, l'action de correction rapide reste limitee a l'apercu (30 premieres lignes) tant que la contrainte n'est pas levee.
