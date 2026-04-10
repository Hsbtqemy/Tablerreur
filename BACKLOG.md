# Backlog Tablerreur — Validation par colonne & UX

> Dernière mise à jour : avril 2026 — **§12 (flux import / modèle)** : **livré (6/6)** — FLUX-03 : confirmation + texte d’aide + toast après changement de modèle si réglages colonne déjà enregistrés (`app.js`, `index.html`). Vérifiée contre le code du dépôt ; backlog audit exécutable en fin de document.
> Statuts : **Fait** | **Prochaine itération** | **Backlog** | **Long terme**

**Révision avril 2026** : synchronisation avec `src/spreadsheet_qa/web/`, `src-tauri/src/main.rs` et `core/`. Les entrées ci-dessous reflètent l’état **actuel** du code ; les lignes obsolètes (ex. « menu Aide non câblé ») ont été corrigées.

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

| Priorité | Thème | Idées | Faisabilité | État code (avril 2026) |
|----------|--------|--------|-------------|-------------------------|
| **P0 — Haute** | Distribution | Menu Aide → URL releases | 🟢 | **Fait** — `src-tauri/src/main.rs` ouvre la page releases du dépôt au clic sur « Vérifier les mises à jour ». |
| **P1 — Moyenne** | Flux UX | **Prévisualisation des données** (aperçu `GET /preview` à l’étape **Configurer**), **choix du modèle** (builtin / overlay NAKALA / YAML) sur **Configurer** — pas sur Téléverser | 🟡 | **Fait (§12)** — `POST /api/jobs` + `PATCH …/template` ; **FLUX-03** : dialogue de confirmation et rappel de fusion si l’utilisateur a déjà enregistré des réglages colonne. |
| **P1 — Moyenne** | Curation & édition | Étape Curation dédiée, persistance, export après curation, curation ciblée | 🟢 | **Partiel** — édition in-place (double-clic), `POST /api/jobs/{id}/edit-cell`, `POST /revalidate`, bandeau « cellules modifiées » ; pas d’étape workflow séparée « Curation ». |
| **P1** | NAKALA — sélection | Sous-ensemble du vocabulaire chargé | 🟢 | **Fait** — `app.js` : sélecteur à cases à cocher après chargement (`#vocab-selector-list`), persistance dans `allowed_values` + `nakala_vocabulary`. |
| **P1** | UX avancée | Caractères invisibles/espaces ; Mapala | 🟢 / 🟡 | **Fait (Tablerreur)** — toggle « Caractères spéciaux » (`renderVisibleChars`), persistance préférence UX. **Fait (Mapala)** — onglet Mapala + API `/api/mapala/*` dans la même app web (`mapala.js`). |
| **P2** | NAKALA — template API | Doc API puis template « NAKALA pur » | 🔴 → 🟡 | **Backlog** — inchangé. |
| **P2** | Presets & règles | Presets ISBN, Date FR, BCP 47, Pays ISO, Lat/Long ; normalisation casse (suggestion) | 🟢 | **Fait** — catalogue UI + backend alignés pour `isbn`, `isbn10`, `isbn13`, `date_fr`, `month_year`, `integer_or_decimal`, `bcp47`, `country_iso`, `latitude`, `longitude`, `email_preset`. **Reste** : normalisation casse en mode suggestion, etc. |
| **P2** | Curation avancée | Undo dans l’étape curation | 🟢 | **Backlog** — undo/redo global des **correctifs** existe ; pas d’historique dédié aux seules éditions manuelles de cellules. |
| **P2** | NAKALA détail | « Une seule valeur », déverrouiller après chargement | 🟢 | **Backlog** — la sélection partielle couvre une partie du besoin ; bouton « Personnaliser » / liste déroulante stricte encore ouverts. |
| **P3 — Basse** | Presets secondaires | slug, intervalle années, code postal FR ; coordonnées east/north | 🟢 / 🔮 | **Partiel** — `url` et `handle` existent désormais comme **presets** du catalogue « Format attendu ». Restent surtout `slug`, intervalle d’années, code postal FR, coordonnées structurées east/north. |
| **Long terme** | Enrichissement | Auto-update Tauri, constructeur visuel regex, détection automatique du format | 🟡 / 🔮 | **Backlog** — inchangé. |

### Faisabilité par bloc (résumé)

- **Briques de base (§1)** : « Valeurs répétées autorisées » (libellé inverse de `unique`) = 🟢, **toujours backlog** (UI n’a que « Valeurs uniques obligatoires »).
- **Presets (§2)** : le catalogue **étendu** dans `app.js` / `index.html` couvre une grande partie de l’ancienne liste « à ajouter » ; voir §2.
- **Cohérence (§4)** : `similar_values` et vocab NAKALA **fait** ; messages NAKALA en français dans le **core** (`nakala_rules.py`) — **fait**.
- **NAKALA sélection (§7A)** : **fait** (UI).
- **NAKALA template (§7B)** : 🔴 tant que l’API NAKALA n’est pas cadrée ; overlay NAKALA à l’upload (`template_id` + `overlay_id`) — **fait**.
- **Curation (§8)** : **partiel** (édition + API + revalidation).
- **Infra (§6)** : signing macOS hors périmètre ; onedir, Dockerfile, limites upload — **fait**.

---

## 1. Briques de base (contrôles par colonne)

### A. Présence et cardinalité

| Fonctionnalité | Statut | Détail |
|---|---|---|
| Valeurs uniques | Fait | `generic.unique_column` — UI web |
| Pseudo-manquants (NA, N/A, null, …) | Fait | `generic.pseudo_missing` — tokens configurables |
| Obligatoire / facultatif par colonne | Fait | `generic.required` |
| Valeurs répétées autorisées (inverse d'unique) | Backlog | Variante UX de `unique` — label inversé dans l'UI (pas de nouvelle règle) |

### B. Forme générale

| Fonctionnalité | Statut | Détail |
|---|---|---|
| Longueur min/max | Fait | `generic.length` — UI web |
| Multiligne autorisé | Fait | `generic.unexpected_multiline` — UI web |
| Nettoyages (trim, espaces, NBSP, invisibles, Unicode, retours ligne) | Fait | Correctifs, étape « Correctifs » du flux web |

### C. Jeu de caractères & casse

| Fonctionnalité | Statut | Détail |
|---|---|---|
| Uniquement chiffres | Fait | Preset `positive_int` ou `content_type: integer` |
| Alphanumérique | Fait | Preset `alphanum` |
| Lettres uniquement | Fait | Preset `letters_only` |
| Interdire certains caractères | Fait | `generic.forbidden_chars` |
| Casse imposée (UPPER / lower / Title) | Fait | `generic.case` |

---

## 2. Presets de format (catalogue regex)

Implémentation : `FORMAT_PRESETS` dans `web/static/app.js` et liste déroulante `#cfg-format-preset` dans `index.html` (groupes : Généraux, Identifiants, Dates, Codes, Avancé).

### Actuellement disponibles (liste alignée sur le code)

| Preset (clé) | Statut | Remarque |
|---|---|---|
| Année, Oui/Non, Alphanumérique, Lettres uniquement, Entier positif | Fait | |
| DOI, ORCID, ARK, ISSN | Fait | |
| ISBN (10 ou 13), ISBN-13, ISBN-10 | Fait | `isbn`, `isbn13`, `isbn10` |
| Adresse e-mail (preset) | Fait | `email_preset` (distinct du `content_type: email`) |
| Handle, URL (preset) | Fait | `handle`, `url` |
| Date W3C-DTF, Date ISO stricte, Date française (JJ/MM/AAAA), Mois / année (MM/AAAA), Mois (libellé) et année | Fait | `w3cdtf`, `iso_date`, `date_fr`, `month_year`, `date_month_words` |
| Langue ISO 639, BCP 47, Pays ISO 3166-1 alpha-2 | Fait | `lang_iso639`, `bcp47`, `country_iso` |
| Entier ou décimal, Latitude, Longitude | Fait | `integer_or_decimal`, `latitude`, `longitude` |
| Personnalisé (regex) | Fait | `custom` |

### Reste à ajouter ou à clarifier

| Preset / besoin | Statut | Priorité |
|---|---|---|
| URL comme entrée du même catalogue « Format attendu » (regex type `https?://…`) | Fait | `url` dans le catalogue + compatibilité `address` / alias legacy `content_type: url` |
| Handle (Handle.net) | Fait | `handle` dans le catalogue, regex backend/web, détection et aperçu |
| Identifiant interne (slug) | Backlog | Basse |
| Intervalle d'années (YYYY-YYYY) | Backlog | Basse |
| Code postal FR | Backlog | Basse |
| Coordonnées « east=…; north=… » (parsing structuré) | Long terme | Basse |

---

## 3. Contrôles « valeurs multiples dans une cellule »

| Fonctionnalité | Statut | Détail |
|---|---|---|
| Liste simple, liste contrôlée, items uniques, min/max items, pas d'items vides | Fait | `generic.list_items` / `generic.allowed_values` (mode liste) |
| Paires clé=valeur | Long terme | Parsing structuré |

---

## 4. Cohérence interne (au-delà du regex)

| Fonctionnalité | Statut | Détail |
|---|---|---|
| Valeurs rares | Fait | `generic.rare_values` |
| Valeurs très proches (rapidfuzz) | Fait | `generic.similar_values` — UI |
| Normalisation suggérée (FR vs Fr vs fr) | Backlog | Extension `generic.case` — mode suggestion |
| Dictionnaire NAKALA + règles `nakala.*` | Fait | + chargement vocab dans l’UI |
| Messages d'erreur des règles `nakala.*` en français | Fait | `core/rules/nakala_rules.py` (libellés FR) |
| Sélection sous-ensemble vocabulaire NAKALA | Fait | Voir §7A |

---

## 5. UX de la configuration par colonne

| Fonctionnalité | Statut | Détail |
|---|---|---|
| Panneau inline, presets groupés, aide, regex avancé, template, Oui/Non, liste verrouillée | Fait | |
| Aperçu temps réel | Fait | `POST /api/jobs/{id}/preview-rule` (debounce 300 ms côté client) |
| Badges colonnes, résumé avant étape suivante, surlignage cellules | Fait | `GET /api/jobs/{id}/preview-issues` |
| Import/export YAML, import vocabulaire, NAKALA, similar_values | Fait | |
| Enrichir le menu « Type de contenu » | Partiel | UI déjà consolidée autour de `text`, `number`, `date`, `boolean`, `language`, `country`, `identifier`, `address` ; types métier supplémentaires éventuels encore à arbitrer |
| Restreindre les formats selon le type choisi | Fait | Filtrage via table de compatibilité + préservation contrôlée des presets legacy incompatibles au chargement |
| Un seul type « Nombre » avec sous-formats | Fait | UI = un seul type visible `number` ; compat ascendante `integer` / `decimal` canonisée côté frontend + API |
| Constructeur visuel de regex | Long terme | |
| Détection automatique du format probable | Long terme | |

#### Types de contenu manquants (candidats)

| Type proposé | Existant en format ? | Priorité |
|-------------|----------------------|----------|
| Texte, Identifiant fusionné, Adresse fusionnée, NAKALA type unique, etc. | Voir `docs/type-format-mapping.md` | Moyenne à basse |

---

## 6. Infrastructure & distribution

| Fonctionnalité | Statut | Détail |
|---|---|---|
| Launcher `python -m spreadsheet_qa.web`, `/health`, Docker, CORS, limites upload, `TABLERREUR_ENV` | Fait | |
| Tauri : sidecar, onedir, splash, menu, health check, icônes | Fait | |
| Tauri : menu Aide → ouvrir URL (releases) | Fait | URL du dépôt configurée dans `main.rs` |
| Tauri : signing macOS | Hors périmètre | |
| Tauri : auto-update | Long terme | Plugin updater |

---

## Ordre recommandé (prochaines sessions)

Pour le **périmètre audit / sécurité / robustesse**, suivre la section **« Backlog audit technique & sécurité (exécutable) »** en fin de document (items `AUD-Px-xx`), en priorité **P0** puis **P1**.

1. **Curation** — Optionnel : étape dédiée, undo local des éditions cellule, parité avec critères §11 (passage Correctifs → Valider si ERROR ouverts).
2. **NAKALA** — Modèles contraignants, vocabulaires auto-appliqués, suggestions de correspondance colonnes → champs NAKALA.
3. **UX config** — Filtre formats par type, fusion type Nombre, presets restants (URL catalogue, code postal, …).
4. **Flux import / modèle (§12)** — **Complet** (y compris FLUX-03). Re-téléversement + `POST` couvrent les sidecars sans `PATCH`.

### Tickets opérationnels (prochaine itération)

#### Curation

- [x] **CUR-01 — Curation ciblée depuis Résultats**
  Objectif : réduire la friction issue → cellule.
  Portée : depuis la liste des problèmes, ouvrir directement la cellule cible en mode édition quand la ligne est visible dans l’aperçu ; garder un fallback clair quand la ligne est hors aperçu.
  Critères d’acceptation : un clic sur l’action de correction ouvre la bonne cellule, le focus est posé dans l’éditeur, et le comportement reste explicite pour les lignes > 30.

- [x] **CUR-02 — Historique visible des éditions manuelles**
  Objectif : distinguer clairement les éditions manuelles des correctifs d’hygiène.
  Portée : UI de statut simple pour les cellules/lignes touchées, libellés d’historique lisibles, et retour utilisateur cohérent lors des undo/redo après édition manuelle.
  Critères d’acceptation : une édition manuelle est identifiable dans l’interface, undo/redo reste compréhensible, et la notion de “lignes touchées” est visible sans relire tout le tableau.

- [ ] **CUR-03 — Décision produit sur une étape Curation dédiée**
  Objectif : trancher entre “édition in-place suffisante” et “vraie étape workflow”.
  Portée : cadrage produit + maquette + règle de passage Correctifs → Valider si une étape dédiée est retenue.
  Critères d’acceptation : décision documentée, emplacement dans le workflow fixé, et liste des impacts code/UI explicitée.

Ordre conseillé : **CUR-01**, puis **CUR-02**. **CUR-03** seulement si le produit veut formaliser une étape distincte.

#### UX config

- [x] **UXCFG-01 — Restreindre les formats selon le type choisi**
  Objectif : supprimer les combinaisons type/format incohérentes dans le panneau Configurer.
  Portée : filtrage du menu “Format attendu” selon la table de compatibilité de `docs/type-format-mapping.md`, avec conservation propre des valeurs existantes lors du chargement d’un job.
  Critères d’acceptation : le menu se réduit quand un type est choisi, les formats incompatibles ne sont plus proposés, et aucun réglage existant n’est perdu silencieusement.
  Vérifié : `format_compat_helpers.js`, filtrage `CONTENT_TYPE_FORMAT_COMPAT` dans `app.js`, préservation contrôlée des presets incompatibles au chargement, tests JS ciblés.

- [x] **UXCFG-02 — Fusionner “Nombre entier” et “Nombre décimal” en type “Nombre”**
  Objectif : simplifier le modèle mental côté utilisateur.
  Portée : libellés UI, normalisation frontend/backend, compatibilité ascendante des configs existantes et des suggestions automatiques.
  Critères d’acceptation : un seul type “Nombre” visible en UI, anciens jobs/configs encore relus correctement, et les presets `integer` / `decimal` restent exploitables.
  Vérifié : UI visible en `number` unique ; alias legacy `integer` / `decimal` relus et canonisés en `number + preset` côté frontend, API, import/export template et validation.

- [x] **UXCFG-03 — Ajouter les presets prioritaires manquants**
  Objectif : compléter les cas concrets encore absents du menu Format.
  Portée : date FR (`DD/MM/YYYY`), mois-année (`MM/YYYY`), `ISBN`, `Handle`, `entier_ou_decimal`, `latitude`, `longitude` ; tests backend + web alignés.
  Critères d’acceptation : chaque preset apparaît dans le menu, la validation associée existe, et des tests dédiés couvrent au moins un cas valide et un cas invalide.
  Vérifié : presets présents dans `index.html` / `app.js`, regex backend via `preview-rule`, détection de format web/core, et cas valides/invalides couverts sur les presets prioritaires.

Ordre conseillé : **UXCFG-01**, puis **UXCFG-02**, puis **UXCFG-03**.

#### NAKALA

- [ ] **NAK-01 — Documenter précisément l’API NAKALA utile au template**
  Objectif : arrêter les hypothèses sur le schéma réellement exposé.
  Portée : doc technique courte listant endpoints, champs utiles, vocabulaires, contraintes, zones d’incertitude et mapping vers Tablerreur.
  Critères d’acceptation : une source de vérité unique existe dans `docs/`, suffisante pour implémenter le template sans relecture manuelle de l’API à chaque fois.

- [ ] **NAK-02 — Générer un template “NAKALA pur”**
  Objectif : proposer un template prêt à l’emploi dérivé du schéma confirmé.
  Portée : template builtin ou généré, couvrant les champs centraux et les règles minimales attendues pour un dépôt NAKALA.
  Critères d’acceptation : un utilisateur peut appliquer ce template sur un job et obtenir une configuration NAKALA cohérente sans réglage manuel colonne par colonne.

- [ ] **NAK-03 — Ajouter le mode “une seule valeur” et le bouton “Personnaliser”**
  Objectif : rendre exploitable la sélection partielle de vocabulaire au quotidien.
  Portée : UI de verrouillage sur une valeur unique, puis déverrouillage/reprise de l’édition de la liste chargée.
  Critères d’acceptation : après chargement d’un vocabulaire, l’utilisateur peut forcer une seule valeur ou revenir à une personnalisation libre, et l’état est persisté dans `column-config`.

- [ ] **NAK-04 — Clarifier la cohérence entre règles NAKALA et sous-ensemble sélectionné**
  Objectif : éviter des messages contradictoires entre vocabulaire API et liste filtrée localement.
  Portée : décision explicite sur la règle de priorité, puis alignement des messages/règles côté backend et UI.
  Critères d’acceptation : la validation applique une logique unique et documentée, et les messages d’erreur reflètent cette logique.

- [x] **NAK-05 — Auto-appliquer les vocabulaires imposés par le modèle NAKALA**
  Objectif : faire du modèle NAKALA une vraie contrainte active dès son application, sans étape manuelle “Charger”.
  Portée : pour les colonnes portant `nakala_vocabulary` et/ou `allowed_values` dans les overlays NAKALA, charger automatiquement le vocabulaire utile, afficher immédiatement le domaine autorisé, et persister cet état dans `column-config`.
  Critères d’acceptation : sur `nakala:type`, `nakala:license`, `dcterms:type`, `dcterms:license` et les autres champs NAKALA concernés, l’utilisateur voit directement les valeurs autorisées par le modèle ; aucune action manuelle n’est requise pour rendre la contrainte visible.
  Vérifié : préchargement silencieux des vocabulaires configurés, auto-chargement à l’ouverture d’une colonne NAKALA, helper `nakala_vocab_helpers.js`, et exposition de `dcterms:language` avec `nakala_vocabulary: "languages"` dans l’overlay étendu.

- [ ] **NAK-06 — Séparer le domaine autorisé par le modèle du sous-ensemble choisi par l’utilisateur**
  Objectif : éviter que `allowed_values` serve à la fois de contrainte modèle et de sélection utilisateur.
  Portée : clarifier et implémenter deux niveaux distincts : 1) domaine autorisé par le modèle NAKALA ; 2) sous-ensemble éventuellement retenu par l’utilisateur pour son jeu de données. Aligner backend, UI et messages de validation.
  Critères d’acceptation : le modèle continue de représenter le domaine NAKALA autorisé, l’utilisateur peut le restreindre explicitement sans perdre cette information, et les messages d’erreur reflètent correctement le niveau de contrainte appliqué.

- [ ] **NAK-07 — Rendre le sélecteur de vocabulaire exploitable sur les gros référentiels**
  Objectif : supprimer la limite pratique actuelle sur les vocabulaires volumineux (licences, langues).
  Portée : remplacer l’affichage tronqué aux 100 premières valeurs par un mécanisme robuste (recherche sur l’ensemble du vocabulaire, pagination ou virtualisation), en conservant compteurs et sélection partielle.
  Critères d’acceptation : une valeur présente au-delà des 100 premières entrées peut être retrouvée et sélectionnée depuis l’UI, sans contournement manuel.

- [x] **NAK-08 — Proposer des correspondances colonnes → champs NAKALA lors du choix d’un modèle**
  Objectif : aider l’utilisateur quand les colonnes du fichier ne portent pas déjà les noms exacts `nakala:*` / `dcterms:*`.
  Portée : heuristiques de suggestion basées sur le nom de colonne (alias, motifs, vocabulaire courant) et, si utile, sur le format détecté ; affichage de propositions confirmables par l’utilisateur lors de l’application d’un modèle NAKALA.
  Critères d’acceptation : des colonnes comme `title`, `licence`, `language`, `creator_name` ou variantes proches déclenchent une suggestion explicite vers un champ NAKALA pertinent ; aucune correspondance n’est appliquée silencieusement.
  Vérifié : endpoint `GET /api/jobs/{id}/template-metadata`, helper `nakala_template_match_helpers.js`, bloc UI “Correspondances suggérées” dans la bande modèle avec application explicite unitaire ou en lot, et test d’intégration sur l’application de la config `nakala:creator` à une colonne alias.

- [x] **NAK-09 — Étendre les alias et motifs reconnus pour les champs NAKALA fréquents**
  Objectif : rendre les suggestions de correspondance réellement utiles sur des fichiers hétérogènes.
  Portée : définir et maintenir un petit référentiel d’alias/motifs par champ cible (ex. `title`, `main_title`, `lang_title` → `nakala:title` ou `dcterms:title`; `language`, `lang`, `iso_lang` → `dcterms:language`).
  Critères d’acceptation : le référentiel est documenté et testé ; les suggestions couvrent les cas courants sans sur-généraliser.
  Vérifié : référentiel étendu dans `nakala_template_match_helpers.js` avec support des groupes de colonnes (`nakala:title_*`, `keywords_*`, `dcterms:identifier*`, etc.), documentation dédiée dans `docs/nakala-template-matching.md`, et tests JS ciblés sur alias exacts et motifs.

Ordre conseillé : **NAK-01**, puis **NAK-02**, puis **NAK-06**, puis **NAK-07**, puis **NAK-08**, puis **NAK-09**, en gardant **NAK-03** et **NAK-04** comme raffinements UX/règles à intégrer dans ce chantier.

---

## 7. Vocabulaires NAKALA — sélection et templates

### A. Sélection dans le vocabulaire chargé

| Idée | Statut | Détail |
|------|--------|--------|
| Choisir un sous-ensemble après chargement | Fait | Cases à cocher dans le panneau colonne (`app.js`) |
| Option « une seule valeur » / liste déroulante stricte | Backlog | |
| Déverrouiller / personnaliser après chargement | Backlog | Bouton « Personnaliser » |
| Cohérence règles NAKALA vs sous-ensemble | Backlog | Comportement à trancher si besoin |

### B. Template depuis l'API NAKALA

| Idée | Statut | Détail |
|------|--------|--------|
| Découverte champs / schéma via API | Backlog | À préciser |
| Génération template « NAKALA pur » | Backlog | |
| Documentation API officielle | Backlog | Préalable |
| **Overlay NAKALA à l’upload** (`generic_default` + `nakala_baseline` / `nakala_extended`) | Fait | `doUpload()` envoie `template_id` + `overlay_id` — **évolution possible** : §12 (modèle déplacé vers Configurer) |

Les autres lignes (libellé ↔ URI, champs dcterms, DataCite, collections, etc.) restent **Backlog** — voir `docs/nakala-validation-formats.md` et `docs/nakala.md`.

### Ordre suggéré (NAKALA)

1. **Documentation** : confirmer ce que l'API expose.
2. **Affinements** : personnalisation liste, template API.
3. **Sélection** : déjà en place ; ajuster cohérence règles si nécessaire.

---

## 8. Étape curation — édition manuelle des cellules

| Idée | Statut | Détail |
|------|--------|--------|
| Étape « Curation » dédiée dans le workflow | Backlog | Pas d’étape séparée aujourd’hui |
| Édition in-place sur le tableau d'aperçu | Fait | Double-clic ; `POST .../edit-cell` |
| Curation ciblée (issue → cellule) | Fait | Depuis Résultats : localisation + ouverture directe en mode édition pour les lignes visibles dans l’aperçu ; fallback explicite hors aperçu |
| Persistance + revalidation | Fait | `POST .../revalidate` |
| Historique / undo éditions manuelles | Fait | Résumé visible des cellules/lignes touchées depuis la dernière validation + libellés undo/redo enrichis dans l’UI |
| Export reflétant les edits | Fait | Données du job à jour ; export de travail disponible dès Correctifs + résultats finaux |

---

## 9. UX avancée — nouveaux items

| Idée | Statut | Détail |
|------|--------|--------|
| Visibilité des caractères invisibles/espaces | Fait | Toggle « Caractères spéciaux » (aperçu + résultats) |
| Intégration Mapala | Fait | Onglet Mapala, `mapala.js`, endpoints `/api/mapala/*` dans la même application |

---

## 10. Décisions — statuts des anomalies (état code)

**État actuel (interface)** : les statuts **OPEN**, **IGNORED** et **EXCEPTED** sont affichés et actionnables (filtres, ignorer / exclure / rouvrir).

> **Note** : une décision antérieure (mars 2026) mentionnait de ne garder que OPEN et IGNORED côté UX et de masquer EXCEPTED. Le **code actuel** expose les trois — cette section a été alignée sur le dépôt. Si le produit doit revenir à l’ancienne règle, il faudra modifier `app.js` + textes.

- Pas de justification obligatoire pour ignorer une anomalie.

---

## 11. Décision — Export depuis l'étape Correctifs

**Décision** : ajouter un **export de travail** depuis l’étape **Correctifs** (étape **3** du flux : Téléverser → Configurer → **Correctifs** → Valider → Résultats), pour sortir un tableur annoté avant la validation finale.

**État technique** : ✅ **implémenté** — endpoints `POST /api/jobs/{id}/exports/annotated` et `.../exports/issues-report` branchés côté `app.py`, avec UI dédiée dans l’étape Correctifs.

**Périmètre backend livré** :

- `POST /api/jobs/{job_id}/exports/annotated`
- `POST /api/jobs/{job_id}/exports/issues-report`
- Options : périmètre (`all|issues|blocking|touched`), marquage visuel, colonne statut, only_open.
- Formats actuellement exposés : tableur annoté `xlsx` (UI) ou `csv` (API), rapport d'anomalies `csv` (UI) ou `txt` (API).

**Critères d'acceptation** (référence produit) :

- Export depuis Correctifs sans terminer tout le workflow. ✅
- Passage Correctifs → Valider : soumis à la politique d’erreurs (voir maquette / spec).
- Re-validation après éditions : `POST /revalidate` existe déjà.

---

## 12. Flux Téléverser — prévisualisation d’abord, modèle à l’étape Configurer

**Objectif** : réduire la friction sur la première étape : **Téléverser** = **fichier + options d’import** uniquement ; **premier aperçu des données** et **choix du modèle** (builtin, overlay NAKALA, import YAML) sur **Configurer** (« je définis les règles »).

**Contexte technique** : `POST /api/jobs` enregistre `template_id` / `overlay_id` (le frontend envoie le choix du sélecteur `#template-id`, présent dans le DOM dès le chargement). `GET /api/jobs/{id}/column-config` fusionne template et surcharges utilisateur (`TemplateManager.compile_config`). **`PATCH /api/jobs/{job_id}/template`** met à jour le modèle sur un job existant (changement après création — ex. sidecar régénéré avec la route). La **fusion** si la config colonne a déjà été touchée : comportement actuel = merge dans `GET /column-config` ; **FLUX-03** = clarifier côté UX (message).

**État global** : 🟢 **6/6 tâches faites**.

### Tâches (découpage)

- [x] **FLUX-01 — UX étape Téléverser** : Bloc « Modèle de validation » retiré de l’étape 1 ; **aperçu des données** = tableau à l’étape **Configurer** (API inchangée : `GET /api/jobs/{id}/preview`).
- [x] **FLUX-02 — API mise à jour du modèle sur job existant** : `PATCH /api/jobs/{job_id}/template` (JSON `template_id`, `overlay_id`) + persistance `job_manager`.
- [x] **FLUX-03 — Règles de fusion / message UX** : Si l’utilisateur a **déjà enregistré** des réglages colonne (`PUT` réussi) puis **change de modèle**, **confirmation** (`confirm`) expliquant la fusion ; **toast** informatif après succès si réglages préexistants ; paragraphe d’aide sous le sélecteur dans `index.html`. Comportement serveur inchangé (`GET /column-config` = merge).
- [x] **FLUX-04 — UX étape Configurer** : Sélecteur de modèle en tête de l’étape + « Importer un modèle » (YAML).
- [x] **FLUX-05 — Frontend** : `doUpload()` envoie dans le **`POST`** les `template_id` / `overlay_id` lus depuis `#template-id` (préférences utilisateur), puis passage à **Configurer** — **pas** `PATCH` obligatoire après création (compatibilité sidecars anciens). Changement de modèle sur **Configurer** : `PATCH` + rechargement aperçu quand le serveur expose la route ; sinon message invitant à re-téléverser ou à mettre à jour l’app.
- [x] **FLUX-06 — Tests** : `tests/test_web_job_template_patch.py` — PATCH overlay + 404 job inconnu.

---

## Backlog audit technique & sécurité (exécutable)

Synthèse des passes d’audit code (architecture, API, Tauri, core, ops). **Cocher** `- [x]` au fil des implémentations. Identifiants **`AUD-Px-xx`** pour les tickets / commits.

### Légende priorités

| Code | Sens |
|------|------|
| **P0** | Critique — avant exposition réseau large ou release sensible |
| **P1** | Haute — robustesse, sécurité opérationnelle, CI |
| **P2** | Moyenne — cohérence produit, durcissement, dette technique |
| **P3** | Basse — documentation, sensibilisation, long terme |

### P0 — Critique

- [x] **AUD-P0-01** — Si l’API est joignable hors poste isolé : **authentification** ou **réseau privé uniquement** ; documenter « non prévu pour Internet public sans garde-fous » (accès par `job_id` seul). → **`docs/deployment-security.md`**
- [x] **AUD-P0-02** — **`POST /api/mapala/upload`** : plafonner la taille des deux fichiers (ex. aligné sur `TABLERREUR_MAX_UPLOAD_MB` ou variable dédiée) ; éviter un `read()` illimité en mémoire. → **`mapala_routes.py`** + `tests/test_mapala_upload_limit.py`
- [x] **AUD-P0-03** — **Tauri** : au menu **Fichier → Quitter**, **tuer le sidecar** Python comme sur `CloseRequested` (`kill` / `wait` dans `src-tauri/src/main.rs`).

### P1 — Haute priorité

- [x] **AUD-P1-01** — **`engine.py`** : `ValidationResult` + `rule_failures` ; API/UI `échecs_règles`.
- [x] **AUD-P1-02** — **`app.py`** : logs sur exports / régénération ; `job.export_errors` + `avertissements_export` + bandeau résultats.
- [ ] **AUD-P1-03** — **Docker / prod** : CORS autre que `*` par défaut ; aligner **Dockerfile** vs **docker-compose** pour `TABLERREUR_CORS_ORIGINS`.
- [ ] **AUD-P1-04** — **Prod** : désactiver ou restreindre **`/docs`**, **`/redoc`**, **`/openapi.json`** si l’API est exposée.
- [ ] **AUD-P1-05** — **CI** : exécuter **`pytest`** sur les PR (sans `-x` ou job dédié) ; optionnel **ruff** + `scripts/check_english_strings.py` sur `ui/`.
- [ ] **AUD-P1-06** — **Gros CSV** (`dataset.py`) : documenter limites ; envisager streaming / refus au-delà d’un seuil pour limiter l’OOM (double charge mémoire).

### P2 — Priorité moyenne

- [ ] **AUD-P2-01** — **`.ods`** : support réel ou retrait du chemin openpyxl / message d’erreur explicite (`dataset.py`).
- [ ] **AUD-P2-02** — **Erreurs API** : éviter `detail=str(exc)` systématique — message générique client, détail en logs serveur.
- [ ] **AUD-P2-03** — **Rate limiting** (si API partagée) : upload, `validate`, `preview-rule`, Mapala.
- [ ] **AUD-P2-04** — **YAML** (import template) : plafonds taille / profondeur contre DoS parsing.
- [ ] **AUD-P2-05** — **Pickle / multi-tenant** : documenter modèle de confiance (permissions `work_dir`, pas de partage de répertoires entre clients).
- [x] **AUD-P2-06** — **Jobs TTL 1 h** : **expiration glissante** via `last_access_at` à chaque `get`/`update` (`jobs.py`). Message 404 existant côté client.
- [ ] **AUD-P2-07** — **FastAPI** : migrer `@app.on_event("startup")` vers **lifespan**.
- [ ] **AUD-P2-08** — **`pytest.ini`** : ne pas imposer `-x` en CI (override dans la commande CI).
- [ ] **AUD-P2-09** — **Tauri** : optionnellement poll **`GET /health`** au lieu du seul TCP pour « prêt ».
- [ ] **AUD-P2-10** — **Tauri** : durcir **CSP** webview si le périmètre contenu évolue.
- [x] **AUD-P2-11** — Remplacer l’**URL GitHub placeholder** des releases dans `main.rs` par le dépôt réel.
- [ ] **AUD-P2-12** — **`tablerreur-backend.spec`** : éviter chemins absolus ; s’appuyer sur `scripts/build_sidecar.py`.
- [ ] **AUD-P2-13** — **`commands.py` / patch** : ordre persistance vs mutation DataFrame ; documenter ou transactionnaliser le bulk.
- [ ] **AUD-P2-14** — **`issue_store.replace_for_columns`** : optimiser si perf sur gros volumes (éviter `list.remove` répété sur grosses listes).

### P3 — Basse priorité / long terme

- [ ] **AUD-P3-01** — Documenter le risque **injection de formules** à l’ouverture des exports dans Excel (CSV/XLSX).
- [ ] **AUD-P3-02** — Étendre un contrôle **chaînes non françaises** au **`web/static`** (le script actuel cible surtout `ui/` PySide).
- [ ] **AUD-P3-03** — **Lockfile** pip / versions figées pour images Docker et builds reproductibles.
- [ ] **AUD-P3-04** — **Tests** : couvrir **Mapala** (`mapala_routes` / core) dans `tests/`.
- [ ] **AUD-P3-05** — **Accessibilité** : passe clavier / focus / tableaux si besoin institutionnel.
- [ ] **AUD-P3-06** — **Signing macOS**, **auto-update Tauri** : suivre la roadmap distribution existante.

### Suivi

| Champ | Usage |
|--------|--------|
| Branche / PR | Lier `AUD-Px-xx` dans le titre ou la description |
| Fait | Cocher la case et éventuellement noter la date en commentaire de commit |
