# Backlog Tablerreur — Validation par colonne & UX

> Dernière mise à jour : février 2026
> Statuts : ✅ Fait | 🔜 Prochaine itération | 📋 Backlog | 🔮 Long terme

---

## Évaluation et priorités (vue consolidée)

Après évaluation de la **faisabilité** (technique, dépendances, effort) et **priorisation**, voici le classement des idées du backlog.

### Légende faisabilité

| Symbole | Signification |
|--------|----------------|
| 🟢 | Faisable sans blocant — stack actuelle suffisante, effort raisonnable |
| 🟡 | Faisable avec préalable ou effort moyen — doc API, refactor léger, ou UX non triviale |
| 🔴 | À clarifier — dépend d'un acteur externe (API, schéma) ou périmètre à définir |
| 🔮 | Long terme — complexité forte ou priorité métier faible |

### Priorité globale (ordre recommandé)

| Priorité | Thème | Idées | Faisabilité |
|----------|--------|--------|-------------|
| **P0 — Haute** | Distribution | Signing macOS, Menu Aide → URL releases | 🟡 (certificat Apple) / 🟢 |
| **P1 — Moyenne** | Curation & édition | Étape Curation, édition in-place, persistance, export après curation, curation ciblée (issues → cellule) | 🟢 |
| **P1** | NAKALA — sélection | Choisir un sous-ensemble dans le vocabulaire chargé (liste à cocher ou select multiple), cohérence règles NAKALA | 🟢 |
| **P1** | UX avancée | Visibilité des caractères invisibles/espaces dans cellules en erreur, intégration Mapala | 🟢 / 🟡 |
| **P2** | NAKALA — template API | Doc/découverte API NAKALA (préalable), puis génération template « NAKALA pur » | 🔴 → 🟡 (après doc) |
| **P2** | Presets & règles | Presets ISBN, Date FR, BCP 47, Pays ISO, Lat/Long ; normalisation casse (suggestion) | 🟢 |
| **P2** | Curation avancée | Historique / undo dans l'étape curation (réutilisation CommandHistory si pertinent) | 🟢 |
| **P2** | NAKALA détail | Option « une seule valeur », déverrouiller / personnaliser après chargement | 🟢 |
| **P3 — Basse** | Presets secondaires | Email, URL, Handle, slug, intervalle années, code postal FR ; coordonnées east/north (parsing structuré) | 🟢 / 🔮 |
| **Long terme** | Enrichissement | Auto-update Tauri, constructeur visuel regex, détection automatique du format | 🟡 / 🔮 |

### Faisabilité par bloc (résumé)

- **Briques de base (§1)** : Valeurs répétées autorisées = 🟢 (label UI uniquement). Reste 1 item.
- **Presets (§2)** : Actuels tous ✅. Restants 🟢 sauf coordonnées structurées 🔮.
- **Cohérence (§4)** : `similar_values` ✅ exposé dans l'UI ; vocab NAKALA ✅.
- **NAKALA sélection (§7A)** : 🟢 — uniquement UI (checkboxes/select), `allowed_values` déjà géré.
- **NAKALA template (§7B)** : 🔴 tant que l'API NAKALA n'a pas été vérifiée ; 🟡 après doc.
- **Curation (§8)** : 🟢 — endpoints et état job existants ; CommandHistory réutilisable.
- **Infra (§6)** : Signing macOS 🟡 (certificat) ; onedir ✅, Dockerfile ✅, limites upload ✅.

---

## 1. Briques de base (contrôles par colonne)

### A. Présence et cardinalité

| Fonctionnalité | Statut | Détail |
|---|---|---|
| Valeurs uniques | ✅ | `generic.unique_column` — exposé dans UI web |
| Pseudo-manquants (NA, N/A, null, -…) | ✅ | `generic.pseudo_missing` — tokens configurables |
| Obligatoire / facultatif par colonne | ✅ | `generic.required` — signale les cellules vides si `required: true` |
| Valeurs répétées autorisées (inverse d'unique) | 📋 | Variante UX de `unique` — pas de nouvelle règle, juste un label inversé dans l'UI |

### B. Forme générale

| Fonctionnalité | Statut | Détail |
|---|---|---|
| Longueur min/max | ✅ | `generic.length` — exposé dans UI web |
| Multiligne autorisé | ✅ | `generic.unexpected_multiline` — exposé dans UI web |
| Nettoyages (trim, espaces, NBSP, invisibles, Unicode, retours ligne) | ✅ | Correctifs typiques, étape 3 du web |

### C. Jeu de caractères & casse

| Fonctionnalité | Statut | Détail |
|---|---|---|
| Uniquement chiffres | ✅ | Couvert par preset regex `positive_int` ou `content_type: integer` |
| Alphanumérique | ✅ | Couvert par preset regex `alphanum` |
| Lettres uniquement (+ accents, tirets, apostrophes) | ✅ | Couvert par preset regex `letters_only` |
| Interdire certains caractères | ✅ | `generic.forbidden_chars` — config : liste de caractères interdits |
| Casse imposée (UPPER / lower / Title) | ✅ | `generic.case` — config : `case: upper\|lower\|title` |

---

## 2. Presets de format (catalogue regex)

### Actuellement disponibles

| Preset | Statut | Regex |
|---|---|---|
| Année (YYYY) | ✅ | `^\d{4}$` |
| Oui / Non | ✅ | `(?i)^(oui\|non\|…)$` — mapping personnalisable |
| Alphanumérique | ✅ | `^[A-Za-z0-9]+$` |
| Lettres uniquement | ✅ | `^[A-Za-zÀ-ÿ\s\-']+$` |
| Entier positif | ✅ | `^\d+$` |
| Personnalisé (avancé) | ✅ | Champ regex libre |
| DOI | ✅ | `^10\.\d{4,9}/[^\s]+$` |
| ORCID | ✅ | `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` |
| ARK | ✅ | `^ark:/\d{5}/.+$` |
| ISSN | ✅ | `^\d{4}-\d{3}[\dX]$` |
| Date W3C-DTF | ✅ | `^\d{4}(-\d{2}(-\d{2})?)?$` |
| Date ISO stricte (YYYY-MM-DD) | ✅ | `^\d{4}-\d{2}-\d{2}$` |
| Langue ISO 639 (fr, en, de…) | ✅ | `(?i)^[a-z]{2,3}$` |

### À ajouter — Identifiants & liens

| Preset | Statut | Regex / logique | Priorité |
|---|---|---|---|
| Email (comme preset, pas seulement content_type) | 📋 | `^[^@\s]+@[^@\s]+\.[^@\s]+$` | Basse |
| URL (comme preset) | 📋 | `https?://\S+` | Basse |
| ISBN-13 | 📋 | `^97[89]\d{10}$` (sans tirets) | Moyenne |
| ISBN-10 | 📋 | `^\d{9}[\dX]$` | Moyenne |
| Handle | 📋 | `^\d+(\.\d+)*/.+$` | Basse |
| Identifiant interne (slug) | 📋 | `^[a-z0-9\-]+$` | Basse |

### À ajouter — Dates & temps

| Preset | Statut | Regex / logique | Priorité |
|---|---|---|---|
| Date FR (JJ/MM/AAAA) | 📋 | `^\d{2}/\d{2}/\d{4}$` + bornes | Moyenne |
| Intervalle d'années (YYYY-YYYY) | 📋 | `^\d{4}-\d{4}$` | Basse |

### À ajouter — Codes & référentiels

| Preset | Statut | Regex / logique | Priorité |
|---|---|---|---|
| Langue BCP 47 (fr-FR, en-GB, oc…) | 📋 | `^[a-z]{2,3}(-[A-Z]{2})?$` | Moyenne |
| Pays ISO 3166-1 alpha-2 (FR, DE…) | 📋 | Liste fermée 2 lettres majuscules | Moyenne |
| Code postal FR | 📋 | `^\d{5}$` | Basse |

### À ajouter — Nombres & mesures

| Preset | Statut | Détail | Priorité |
|---|---|---|---|
| Latitude | 📋 | Décimal entre -90 et 90 | Moyenne |
| Longitude | 📋 | Décimal entre -180 et 180 | Moyenne |
| Coordonnées "east=…; north=…" | 🔮 | Parsing structuré | Basse |

---

## 3. Contrôles "valeurs multiples dans une cellule"

| Fonctionnalité | Statut | Détail | Priorité |
|---|---|---|---|
| Liste simple (séparateur configurable) : split + trim items | ✅ | `generic.list_items` — config : `list_separator` |  |
| Liste contrôlée : chaque item dans allowed_values | ✅ | Extension de `generic.allowed_values` pour mode liste |  |
| Items uniques dans la liste | ✅ | Option `list_unique: true` |  |
| Nombre min / max d'items | ✅ | Options `list_min_items`, `list_max_items` |  |
| Interdire les items vides | ✅ | Option `list_no_empty: true` (défaut) |  |
| Paires clé=valeur | 🔮 | Parsing structuré | Basse |

---

## 4. Cohérence interne (au-delà du regex)

| Fonctionnalité | Statut | Détail | Priorité |
|---|---|---|---|
| Valeurs rares (suspicion de faute de saisie) | ✅ | `generic.rare_values` — seuil et minimum configurables |  |
| Valeurs très proches (typo probable, similarité) | ✅ | `generic.similar_values` — via rapidfuzz, exposé dans l'UI web (checkbox + seuil) |  |
| Normalisation suggérée (FR vs Fr vs fr) | 📋 | Extension de `generic.case` — mode suggestion | Moyenne |
| Dictionnaire contrôlé distant (vocab NAKALA) | ✅ | `nakala_api.py` + règles `nakala.deposit_type` / `nakala.license` / `nakala.language` ; chargement vocabulaire dans l'UI via endpoint `/api/nakala/vocabulary/{vocab_name}` | Sélection sous-ensemble en backlog |

---

## 5. UX de la configuration par colonne

| Fonctionnalité | Statut | Détail |
|---|---|---|
| Panneau inline au clic sur en-tête | ✅ | Implémenté dans l'étape "Configurer" |
| Dropdown "Format attendu" (presets) | ✅ | 13 presets en 5 groupes (optgroup) |
| Texte d'aide contextuel par preset | ✅ | Exemples valides/invalides |
| Mode regex avancé | ✅ | Champ libre caché par défaut |
| Pré-remplissage depuis template | ✅ | Template → config initiale, éditable |
| Oui/Non avec mapping personnalisable | ✅ | Config : `yes_no_true_values`, `yes_no_false_values` |
| Mode "Sélection" (liste fermée non éditable) | ✅ | `allowed_values_locked: true` — textarea en lecture seule |
| Catégorisation des presets (groupes dans le dropdown) | ✅ | 5 groupes : Généraux, Identifiants, Dates, Codes, Avancé |
| Aperçu temps réel (3 OK / 3 rejetées) | ✅ | Endpoint `POST /preview-rule`, debounce 300ms |
| Badges sur colonnes configurées | ✅ | Point vert `●` sur `<th>`, tooltip résumé |
| Résumé de configuration avant étape suivante | ✅ | Tableau récapitulatif + boutons Modifier / Continuer |
| Surlignage des cellules en erreur dans l'aperçu | ✅ | Endpoint `GET /preview-issues`, classes `cell-error/warning/suspicion` |
| Import de template YAML depuis l'UI | ✅ | Upload `.yaml` à l'étape Upload et à l'étape Configurer ; endpoint `POST /import-template` |
| Export de template YAML depuis l'UI | ✅ | Télécharger la config courante en `.yaml` ; endpoint `GET /export-template` |
| Import de vocabulaire personnalisé | ✅ | Upload `.yaml` de vocabulaire ; endpoint `POST /import-vocabulary` |
| Sélecteur vocabulaire NAKALA dans le panneau | ✅ | Bouton « Charger vocabulaire NAKALA » dans le panneau de config colonne |
| Détection valeurs similaires | ✅ | Checkbox + seuil dans le panneau de config colonne ; `generic.similar_values` via rapidfuzz |
| Enrichir le menu « Type de contenu » | 📋 | Aujourd'hui seulement 5 types (entier, décimal, date, email, URL). Voir ci‑dessous les types manquants. | Moyenne |
| Restreindre les formats attendus selon le type choisi | 📋 | Filtrer le dropdown « Format attendu » selon le type sélectionné (ex. type Date → Année, W3C-DTF, ISO). Voir `docs/type-format-mapping.md`. | Moyenne |
| Un seul type « Nombre » avec formats (entier, décimal, etc.) | 📋 | Fusionner « Nombre entier » et « Nombre décimal » en un type **Nombre** avec formats. Voir `docs/type-format-mapping.md`. | Moyenne |
| Constructeur visuel de regex | 🔮 | Interface drag-and-drop de blocs | Long terme |
| Détection automatique du format probable | 🔮 | Heuristique sur les données chargées | Long terme |

#### Types de contenu manquants (candidats)

| Type proposé | Existant en format ? | Faisabilité | Priorité |
|-------------|----------------------|-------------|----------|
| **Texte** (`text`) | — | Aucun type « texte » actuellement ; formats `alphanum`, `letters_only`, `yes_no` sans type dédié. Voir `docs/type-format-mapping.md`. | Moyenne |
| Année (YYYY) | ✅ `year` | Pas de nouveau type : une année est une date partielle. Garder Type = Date + Format = Année. Déjà couvert. | — |
| Oui / Non (booléen) | ✅ `yes_no` | Peut rester en format uniquement | Basse |
| Code langue (ISO 639) | ✅ `lang_iso639` | Utile pour NAKALA | Moyenne |
| **Identifiant** (DOI, ORCID, ARK, ISSN…) | ✅ presets dédiés | Un seul type **Identifiant** ; formats = DOI, ORCID, ARK, ISSN (puis ISBN, Handle). Voir `docs/type-format-mapping.md`. | Moyenne |
| **Adresse** (e-mail, URL) | ✅ types actuels | Fusionner en un type **Adresse** ; formats = E-mail, URL. Voir `docs/type-format-mapping.md`. | Moyenne |
| **Type NAKALA** | ✅ règles + API | Un seul type **NAKALA** ; formats = Type de ressource, Licence, Langue, Date créée, Créateur. Voir `docs/type-format-mapping.md`. | Basse |
| Texte court / Texte long | — | Variante du type Texte ; longueur min/max + multiligne. | Basse |
| Autres types envisagés | — | **Langue** (ISO 639, BCP 47), **Booléen** (Oui/Non), **Pays** (ISO 3166), **Coordonnées** (lat/long), **URI** (générique). Voir `docs/type-format-mapping.md` §1c. | Basse à Moyenne |

---

## 6. Infrastructure & distribution

| Fonctionnalité | Statut | Détail | Priorité |
|---|---|---|---|
| Launcher standalone (`python -m spreadsheet_qa.web`) | ✅ | Port auto + navigateur | |
| Endpoint `/health` | ✅ | Retourne `{"status": "ok", "version": "..."}` | |
| Tauri — init projet | ✅ | `src-tauri/`, Cargo.toml, tauri.conf.json | |
| Tauri — sidecar Python | ✅ | PyInstaller via `build_sidecar.py` | |
| Tauri — sidecar onedir (démarrage ~1,4s) | ✅ | Mode `--onedir` PyInstaller, dossier `_internal/`, plus d'extraction au lancement | |
| Tauri — splash screen FR | ✅ | HTML embarqué en data URI (`include_str!`), adapté mode sombre | |
| Tauri — menu natif (Fichier, Aide) | ✅ | Fichier → Quitter ; Aide → Vérifier MàJ | |
| Tauri — health check avant navigation | ✅ | Poll TCP toutes les 200ms, port 8400–8500 | |
| Tauri — icône `.icns` / `.ico` / PNG | ✅ | Lettre T blanche, fond bleu #2563eb | |
| Tauri — `.dmg` debug (non signé) | ✅ | Généré via `npm run tauri build` | |
| Déploiement online (Dockerfile) | ✅ | Dockerfile multi-stage (sans PySide6) + docker-compose.yml | |
| Limites upload (taille, types MIME) | ✅ | `TABLERREUR_MAX_UPLOAD_MB`, validation extension/MIME | |
| CORS configurable | ✅ | `TABLERREUR_CORS_ORIGINS` | |
| Variable `TABLERREUR_ENV` (dev/prod) | ✅ | Contrôle comportements dev vs prod | |
| Tauri — menu Aide câblé (ouvre URL releases) | 📋 | Item présent, action non implémentée | Moyenne |
| Tauri — signing macOS (certificat Apple Developer) | 📋 | Nécessaire pour distribuer sans avertissement | Haute |
| Tauri — auto-update | 🔮 | Plugin Tauri updater | Long terme |

---

## Ordre recommandé (prochaines sessions)

1. **Haute priorité — Distribution**
   - Signing macOS (certificat Apple Developer, notarisation)
   - Menu Aide → ouvrir URL GitHub releases

2. **Moyenne priorité — Fonctionnel**
   - Étape Curation (édition in-place des cellules, persistance, export)
   - Sélection d'un sous-ensemble dans le vocabulaire NAKALA chargé
   - Visibilité des caractères invisibles/espaces dans les cellules en erreur

3. **Enrichissement**
   - Presets supplémentaires (ISBN, Date FR, BCP 47, Pays ISO, Lat/Long)
   - NAKALA : template depuis l'API, valeurs spéciales (Inconnue, Anonyme)
   - Auto-update Tauri
   - Détection automatique de format
   - Constructeur visuel de regex

---

## 7. Vocabulaires NAKALA — sélection et templates

### A. Sélection dans le vocabulaire chargé

Actuellement : « Charger le vocabulaire NAKALA » remplit *toute* la liste des valeurs autorisées et la verrouille ; la colonne accepte n'importe quelle valeur du vocabulaire.

| Idée | Statut | Détail | Priorité |
|------|--------|--------|----------|
| Choisir un sous-ensemble dans le vocabulaire chargé | 📋 | Après chargement, permettre de sélectionner une ou plusieurs valeurs (ex. une seule licence, ou quelques types de ressource) au lieu d'accepter l'intégralité du vocabulaire. | Moyenne |
| UI : liste à cocher après chargement | 📋 | Afficher les valeurs du vocabulaire en cases à cocher ; l'utilisateur coche celles qu'il veut autoriser ; `allowed_values` = sélection. | Moyenne |
| UI : select multiple | 📋 | Alternative : `<select multiple>` pour choisir les valeurs ; même résultat (liste filtrée → `allowed_values`). | Moyenne |
| Option « une seule valeur » (liste déroulante) | 📋 | Cas particulier : une seule valeur sélectionnable (ex. « cette colonne = CC-BY-4.0 ») ; `allowed_values` à un élément. | Basse |
| Déverrouiller / personnaliser après chargement | 📋 | Bouton « Personnaliser » pour déverrouiller le textarea et éditer la liste tout en gardant la trace `nakala_vocabulary`. | Basse |
| Cohérence règles NAKALA | 📋 | Si l'utilisateur ne garde qu'un sous-ensemble : les règles `nakala.deposit_type` / `nakala.license` / `nakala.language` pourraient soit utiliser la liste configurée (allowed_values) au lieu du vocabulaire complet, soit rester sur le vocabulaire complet (comportement à trancher). | Moyenne |

### B. Template depuis l'API NAKALA

Créer un template de validation (colonnes + règles) uniquement à partir de ce que l'API NAKALA expose (vocabulaires, champs requis/recommandés), sans repartir d'un YAML builtin.

| Idée | Statut | Détail | Priorité |
|------|--------|--------|----------|
| Découverte des champs NAKALA via l'API | 📋 | Si l'API NAKALA expose une liste de champs (requis / recommandés / optionnels) ou un schéma, l'utiliser pour générer la structure du template. | À préciser |
| Génération de template « NAKALA pur » | 📋 | Endpoint ou flux UI : « Créer un template depuis NAKALA » → appel API → template YAML ou config en mémoire. | Moyenne |
| Template = colonnes + vocabulaires branchés | 📋 | Le template généré attache les vocabulaires aux colonnes correspondantes ; l'utilisateur peut ensuite appliquer la sélection (cf. § A). | Moyenne |
| Documentation / découverte API | 📋 | Vérifier la doc officielle NAKALA (champs, vocabulaires, éventuels endpoints de schéma). Référence : `docs/nakala-validation-formats.md`. | Haute (avant implémentation) |
| Appliquer NAKALA (Référence / Étendu) en overlay à l'upload | 📋 | Corriger : envoyer generic_id=generic_default + overlay_id=nakala_baseline|nakala_extended pour que la config = base générique + overlay NAKALA. | Moyenne |
| Transformation libellé → URI (COAR, etc.) | 📋 | Correctif « Remplacer par l'URI COAR » quand la valeur est un libellé reconnu ; ou mapping libellé → URI à l'import/export. | Moyenne |
| Appliquer le type selon le champ dcterms/nakala souhaité | 📋 | En configuration de colonne : indiquer quel champ dcterms/nakala est ciblé ; l'interface applique vocabulaire et règle adaptés. | Moyenne |
| Afficher les valeurs NAKALA en libellés avec stockage URI | 📋 | Proposer une liste en libellés (image, video, son…) avec stockage/validation en URI. **À vérifier dans la pratique** — ne pas implémenter de suite. | À vérifier |
| Champs dcterms manquants + schéma d'export NAKALA | 📋 | Intégrer dcterms:creator, dcterms:contributor, dcterms:publisher, dcterms:rightsHolder, etc. Voir `docs/nakala.md`. | Moyenne |
| Validation propriétés/encodages via API NAKALA | 📋 | Utiliser `GET /vocabularies/properties` et `GET /vocabularies/metadatatypes` pour valider propriétés et encodages. Voir `docs/nakala-validation-formats.md`. | Moyenne |
| Relations DataCite (RelationType) | 📋 | Valider que le type de relation appartient à la liste fermée DataCite. Voir `docs/nakala-validation-formats.md` §6. | Moyenne |
| Encodages structurés dcterms (Box, Point, Period) | 📋 | Valider les formats dcterms:Box, dcterms:Point, dcterms:Period. Voir `docs/nakala-validation-formats.md` §5. | Basse |
| Collections NAKALA (statut, titre) | 📋 | Support spécifique collections : statut privé/public via `GET /vocabularies/collectionStatuses`. Voir `docs/nakala-validation-formats.md` §7. | Basse |
| Messages d'erreur NAKALA en français | 📋 | Les règles `nakala.*` renvoient des messages en anglais. Traduire pour l'UI web et les exports. Voir `docs/nakala-validation-formats.md` §9.1. | Moyenne |
| Valeurs spéciales NAKALA : « Inconnue » (date), « Anonyme » (créateur) | 📋 | Accepter « Inconnue » pour `nakala:created` et « Anonyme » pour `nakala:creator`. Voir `docs/nakala-validation-formats.md` §9.2. | Moyenne |

### Ordre suggéré (NAKALA)

1. **Documentation** : confirmer ce que l'API NAKALA expose (champs, schéma, vocabulaires). Référence : `docs/nakala-validation-formats.md`.
2. **Sélection** : UI pour choisir un sous-ensemble dans le vocabulaire chargé, puis cohérence avec les règles NAKALA.
3. **Template depuis l'API** : génération d'un template (colonnes + règles) à partir des données NAKALA disponibles.

---

## 8. Étape curation — édition manuelle des cellules

Possibilité pour l'utilisateur de modifier directement certaines cellules dans l'interface (correction manuelle, curation), dans une étape dédiée ou intégrée au flux actuel.

| Idée | Statut | Détail | Priorité |
|------|--------|--------|----------|
| Étape « Curation » dans le workflow | 📋 | Ajouter une étape (ex. après Validation ou Correctifs) où l'utilisateur peut éditer les valeurs du tableau : clic sur une cellule → édition in-place, sauvegarde dans le job. | Moyenne |
| Édition in-place dans le tableau d'aperçu | 📋 | Rendre les cellules du tableau d'aperçu éditables : focus → saisie → validation → mise à jour du DataFrame côté backend. | Moyenne |
| Curation ciblée (cellules en erreur) | 📋 | Proposer d'éditer en priorité les cellules signalées par la validation (liste des issues → clic → ouvrir la cellule en édition avec suggestion si disponible). | Moyenne |
| Persistance des modifications | 📋 | Les changements de curation doivent être renvoyés au backend (endpoint type PATCH/PUT sur les données du job), re-validation optionnelle après édition. | Moyenne |
| Historique / annuler une modification | 📋 | Undo/redo dans l'étape curation (peut s'appuyer sur `CommandHistory` / `ApplyCellFixCommand` côté core). | Basse |
| Export après curation | 📋 | S'assurer que l'export (CSV, XLSX) reflète les valeurs éditées lors de la curation. | Moyenne |

---

## 9. UX avancée — nouveaux items

| Idée | Statut | Détail | Priorité |
|------|--------|--------|----------|
| Visibilité des caractères invisibles/espaces | 📋 | Dans les cellules signalées par `generic.hygiene.invisible_chars` ou `generic.hygiene.leading_trailing_space`, afficher visuellement les caractères problématiques (ex. pilcrow ¶, point médian ·, surlignage) pour que l'utilisateur comprenne l'erreur. | Moyenne |
| Intégration Mapala | 📋 | Intégration avec Mapala (mapping de tableur) dans le même Tauri ou en fenêtre liée. Périmètre à définir. | À préciser |
