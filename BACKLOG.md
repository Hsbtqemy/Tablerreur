# Backlog Tablerreur — Validation par colonne & UX

> Dernière mise à jour : février 2026
> Statuts : ✅ Fait | 🔜 Prochaine itération | 📋 Backlog | 🔮 Long terme

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
| Valeurs très proches (typo probable, similarité) | 🔮 | `generic.similar_values` existe mais non exposé dans l'UI web | Basse |
| Normalisation suggérée (FR vs Fr vs fr) | 📋 | Extension de `generic.case` — mode suggestion | Moyenne |
| Dictionnaire contrôlé distant (vocab NAKALA) | 🔮 | `nakala_api.py` existe, pas encore intégré aux règles | Long terme |

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
| Import de template YAML depuis l'UI | 📋 | Permettre d'uploader un fichier `.yaml` de config | Moyenne |
| Constructeur visuel de regex | 🔮 | Interface drag-and-drop de blocs | Long terme |
| Détection automatique du format probable | 🔮 | Heuristique sur les données chargées | Long terme |

---

## 6. Infrastructure & distribution

| Fonctionnalité | Statut | Détail | Priorité |
|---|---|---|---|
| Launcher standalone (`python -m spreadsheet_qa.web`) | ✅ | Port auto + navigateur | |
| Endpoint `/health` | ✅ | Retourne `{"status": "ok", "version": "..."}` | |
| Tauri — init projet | ✅ | `src-tauri/`, Cargo.toml, tauri.conf.json | |
| Tauri — sidecar Python | ✅ | PyInstaller via `build_sidecar.py` | |
| Tauri — splash screen FR | ✅ | HTML embarqué en data URI (`include_str!`) | |
| Tauri — menu natif (Fichier, Aide) | ✅ | Fichier → Quitter ; Aide → Vérifier MàJ | |
| Tauri — health check avant navigation | ✅ | Poll TCP toutes les 200ms, port 8400–8500 | |
| Tauri — icône `.icns` / `.ico` / PNG | ✅ | Lettre T blanche, fond bleu #2563eb | |
| Tauri — `.dmg` debug (non signé) | ✅ | Généré via `npm run tauri build` | |
| Tauri — menu Aide câblé (ouvre URL releases) | 📋 | Item présent, action non implémentée | Moyenne |
| Tauri — signing macOS (certificat Apple Developer) | 📋 | Nécessaire pour distribuer sans avertissement | Haute |
| Tauri — auto-update | 🔮 | Plugin Tauri updater | Long terme |
| Déploiement online (Dockerfile) | 📋 | FastAPI + static, variables d'env | Moyenne |
| Limites upload (taille, types MIME) | 📋 | Configurable par env var | Moyenne |
| Réduction taille sidecar (onedir au lieu de onefile) | 📋 | Démarrage plus rapide (~5s vs ~30s) | Haute |

---

## Ordre recommandé (prochaines sessions)

1. **Haute priorité — Distribution**
   - Signing macOS (certificat Apple Developer, notarisation)
   - Sidecar en mode `onedir` pour réduire le délai de démarrage (30s → 5s)
   - Menu Aide → ouvrir URL GitHub releases

2. **Moyenne priorité — Fonctionnel**
   - Import de template YAML depuis l'UI web
   - Déploiement online (Dockerfile + limites upload)
   - `generic.similar_values` exposé dans l'UI web

3. **Long terme — Enrichissement**
   - Vocabulaires distants NAKALA intégrés aux règles
   - Auto-update Tauri
   - Détection automatique de format
   - Constructeur visuel de regex

---

## 7. Vocabulaires NAKALA — sélection et templates

### A. Sélection dans le vocabulaire chargé

Actuellement : « Charger le vocabulaire NAKALA » remplit *toute* la liste des valeurs autorisées et la verrouille ; la colonne accepte n’importe quelle valeur du vocabulaire.

| Idée | Statut | Détail | Priorité |
|------|--------|--------|----------|
| Choisir un sous-ensemble dans le vocabulaire chargé | 📋 | Après chargement, permettre de sélectionner une ou plusieurs valeurs (ex. une seule licence, ou quelques types de ressource) au lieu d’accepter l’intégralité du vocabulaire. | Moyenne |
| UI : liste à cocher après chargement | 📋 | Afficher les valeurs du vocabulaire en cases à cocher ; l’utilisateur coche celles qu’il veut autoriser ; `allowed_values` = sélection. | Moyenne |
| UI : select multiple | 📋 | Alternative : `<select multiple>` pour choisir les valeurs ; même résultat (liste filtrée → `allowed_values`). | Moyenne |
| Option « une seule valeur » (liste déroulante) | 📋 | Cas particulier : une seule valeur sélectionnable (ex. « cette colonne = CC-BY-4.0 ») ; `allowed_values` à un élément. | Basse |
| Déverrouiller / personnaliser après chargement | 📋 | Bouton « Personnaliser » pour déverrouiller le textarea et éditer la liste (ajouter/supprimer des lignes) tout en gardant la trace `nakala_vocabulary`. | Basse |
| Cohérence règles NAKALA | 📋 | Si l’utilisateur ne garde qu’un sous-ensemble : les règles `nakala.deposit_type` / `nakala.license` / `nakala.language` pourraient soit utiliser la liste configurée (allowed_values) au lieu du vocabulaire complet, soit rester sur le vocabulaire complet (comportement à trancher). | Moyenne |

### B. Template depuis l’API NAKALA

Créer un template de validation (colonnes + règles) uniquement à partir de ce que l’API NAKALA expose (vocabulaires, champs requis/recommandés), sans repartir d’un YAML builtin.

| Idée | Statut | Détail | Priorité |
|------|--------|--------|----------|
| Découverte des champs NAKALA via l’API | 📋 | Si l’API NAKALA expose une liste de champs (requis / recommandés / optionnels) ou un schéma, l’utiliser pour générer la structure du template (colonnes, kinds, règles). | À préciser |
| Génération de template « NAKALA pur » | 📋 | Endpoint ou flux UI : « Créer un template depuis NAKALA » → appel API (vocabulaires + métadonnées si dispo) → template YAML ou config en mémoire (colonnes, `nakala.deposit_type` / `nakala.license` / `nakala.language` / `nakala.created_format` sur les bons champs). | Moyenne |
| Template = colonnes + vocabulaires branchés | 📋 | Le template généré attache les vocabulaires (datatypes, licenses, languages) aux colonnes correspondantes ; l’utilisateur peut ensuite appliquer la sélection (cf. § A) si l’option est en place. | Moyenne |
| Documentation / découverte API | 📋 | Vérifier la doc officielle NAKALA (champs, vocabulaires, éventuels endpoints de schéma) pour cadrer la génération de template. | Haute (avant implémentation) |

### Ordre suggéré (NAKALA)

1. **Documentation** : confirmer ce que l’API NAKALA expose (champs, schéma, vocabulaires).
2. **Sélection** : UI pour choisir un sous-ensemble dans le vocabulaire chargé (liste à cocher ou select multiple), puis cohérence avec les règles NAKALA.
3. **Template depuis l’API** : génération d’un template (colonnes + règles) à partir des données NAKALA disponibles.

---

## 8. Étape curation — édition manuelle des cellules

Possibilité pour l'utilisateur de modifier directement certaines cellules dans l'interface (correction manuelle, curation), dans une étape dédiée ou intégrée au flux actuel.

| Idée | Statut | Détail | Priorité |
|------|--------|--------|----------|
| Étape « Curation » dans le workflow | 📋 | Ajouter une étape (ex. après Validation ou Correctifs) où l'utilisateur peut éditer les valeurs du tableau : clic sur une cellule → édition in-place ou dans un panneau, sauvegarde dans le job. | Moyenne |
| Édition in-place dans le tableau d'aperçu | 📋 | Rendre les cellules du tableau d'aperçu (étape Configurer ou Résultats) éditables : focus → saisie → validation → mise à jour du DataFrame côté backend. | Moyenne |
| Curation ciblée (cellules en erreur) | 📋 | Proposer d'éditer en priorité les cellules signalées par la validation (liste des issues → clic → ouvrir la cellule en édition avec suggestion si disponible). | Moyenne |
| Persistance des modifications | 📋 | Les changements de curation doivent être renvoyés au backend (endpoint type PATCH/PUT sur les données du job), re-validation optionnelle après édition. | Moyenne |
| Historique / annuler une modification | 📋 | Undo/redo ou journal des modifications dans l'étape curation (peut s'appuyer sur `CommandHistory` / `ApplyCellFixCommand` côté core si réutilisé). | Basse |
| Export après curation | 📋 | S'assurer que l'export (CSV, XLSX) reflète les valeurs éditées lors de la curation. | Moyenne |
