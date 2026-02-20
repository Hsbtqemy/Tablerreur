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
| Obligatoire / facultatif par colonne | 📋 | Nouvelle règle `generic.required` — signale les cellules vides si `required: true` |
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
| Interdire certains caractères | 📋 | Nouvelle règle `generic.forbidden_chars` — config : liste de caractères interdits |
| Casse imposée (UPPER / lower / Title) | 📋 | Nouvelle règle `generic.case` — config : `case: upper\|lower\|title` |

---

## 2. Presets de format (catalogue regex)

### Actuellement disponibles

| Preset | Statut | Regex |
|---|---|---|
| Année (YYYY) | ✅ | `^\d{4}$` |
| Oui / Non | ✅ | `(?i)^(oui\|non\|o\|n\|yes\|no\|vrai\|faux\|true\|false\|1\|0)$` |
| Alphanumérique | ✅ | `^[A-Za-z0-9]+$` |
| Lettres uniquement | ✅ | `^[A-Za-zÀ-ÿ\s\-']+$` |
| Entier positif | ✅ | `^\d+$` |
| Personnalisé (avancé) | ✅ | Champ regex libre |

### À ajouter — Identifiants & liens

| Preset | Statut | Regex / logique | Priorité |
|---|---|---|---|
| Email | 🔜 | `^[^@\s]+@[^@\s]+\.[^@\s]+$` (déjà dans content_type, à dupliquer en preset) | Haute |
| URL | 🔜 | `https?://\S+` ou `www\.\S+` (idem) | Haute |
| DOI | 🔜 | `^10\.\d{4,9}/[^\s]+$` | Haute (SHS/NAKALA) |
| ORCID | 🔜 | `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` | Haute (SHS/NAKALA) |
| ARK | 🔜 | `^ark:/\d{5}/.+$` | Haute (SHS/NAKALA) |
| ISSN | 📋 | `^\d{4}-\d{3}[\dX]$` | Moyenne |
| ISBN-13 | 📋 | `^97[89]\d{10}$` (sans tirets) ou avec tirets | Moyenne |
| ISBN-10 | 📋 | `^\d{9}[\dX]$` | Moyenne |
| Handle | 📋 | `^\d+(\.\d+)*/.+$` | Basse |
| Identifiant interne (slug) | 📋 | `^[a-z0-9\-]+$` ou `^[A-Z0-9_]+$` | Basse |

### À ajouter — Dates & temps

| Preset | Statut | Regex / logique | Priorité |
|---|---|---|---|
| Date W3C-DTF (YYYY ou YYYY-MM ou YYYY-MM-DD) | 🔜 | `^\d{4}(-\d{2}(-\d{2})?)?$` + contrôle bornes | Haute (NAKALA) |
| Date complète ISO (YYYY-MM-DD strict) | 📋 | `^\d{4}-\d{2}-\d{2}$` + bornes | Moyenne |
| Date FR (JJ/MM/AAAA) | 📋 | `^\d{2}/\d{2}/\d{4}$` + bornes | Moyenne |
| Intervalle d'années (YYYY-YYYY) | 📋 | `^\d{4}-\d{4}$` | Basse |

### À ajouter — Codes & référentiels

| Preset | Statut | Regex / logique | Priorité |
|---|---|---|---|
| Langue ISO 639-1 (fr, en, de…) | 🔜 | Liste fermée 2 lettres minuscules | Haute (NAKALA) |
| Langue BCP 47 (fr-FR, en-GB, oc…) | 📋 | `^[a-z]{2,3}(-[A-Z]{2})?$` | Moyenne |
| Pays ISO 3166-1 alpha-2 (FR, DE…) | 📋 | Liste fermée 2 lettres majuscules | Moyenne |
| Code postal FR | 📋 | `^\d{5}$` | Basse (trop spécifique) |

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
| Liste simple (séparateur \|) : split + trim items | 📋 | Nouvelle règle `generic.list_items` — config : `list_separator` | Haute |
| Liste contrôlée (\|) : chaque item dans allowed_values | 📋 | Extension de `generic.allowed_values` pour mode liste | Haute |
| Items uniques dans la liste | 📋 | Option `list_unique: true` | Moyenne |
| Max items | 📋 | Option `list_max_items: N` | Basse |
| Paires clé=valeur | 🔮 | Parsing structuré | Basse |

---

## 4. Cohérence interne (au-delà du regex)

| Fonctionnalité | Statut | Détail | Priorité |
|---|---|---|---|
| Valeurs rares (suspicion : n'apparaît qu'1 fois) | 📋 | Nouvelle règle `generic.rare_values` — seuil configurable | Moyenne |
| Valeurs très proches (typo probable, similarité) | 🔮 | Nécessite rapidfuzz ou équivalent — nouvelle dépendance | Basse |
| Normalisation suggérée (FR vs Fr vs fr) | 📋 | Extension de `generic.case` — mode suggestion | Moyenne |
| Dictionnaire contrôlé distant (vocab NAKALA) | 🔮 | `nakala_api.py` existe, pas encore intégré aux règles | Long terme |

---

## 5. UX de la configuration par colonne

| Fonctionnalité | Statut | Détail | Priorité |
|---|---|---|---|
| Panneau inline au clic sur en-tête | ✅ | Implémenté dans l'étape "Configurer" |  |
| Dropdown "Format attendu" (presets) | ✅ | 6 presets de base |  |
| Texte d'aide contextuel par preset | ✅ | Exemples valides/invalides |  |
| Mode regex avancé | ✅ | Champ libre caché par défaut |  |
| Pré-remplissage depuis template | ✅ | Template → config initiale, éditable |  |
| Oui/Non avec mapping personnalisable (définir quoi = True, quoi = False) | 🔜 | Config : `true_values`, `false_values` | Haute |
| Mode "Sélection" (liste fermée définie dans le template, non éditable par l'utilisateur) | 📋 | Variante de `allowed_values` avec flag `locked: true` | Moyenne |
| Catégorisation des presets (groupes dans le dropdown) | 📋 | Identifiants, Dates, Codes, Nombres… | Moyenne |
| Aperçu temps réel (3 valeurs OK / 3 rejetées de la colonne) | 🔮 | Nécessite analyse côté serveur + endpoint | Long terme |
| Constructeur visuel de regex | 🔮 | Interface drag-and-drop de blocs | Long terme |
| Détection automatique du format probable | 🔮 | Heuristique sur les données chargées | Long terme |

---

## 6. Infrastructure & distribution

| Fonctionnalité | Statut | Détail | Priorité |
|---|---|---|---|
| Launcher standalone (python -m spreadsheet_qa.web) | ✅ | Port auto + navigateur |  |
| Endpoint /health | ✅ | Retourne version |  |
| Tauri — init projet | 📋 | src-tauri/, config, fenêtre | Haute |
| Tauri — sidecar Python | 📋 | PyInstaller + externalBin | Haute |
| Tauri — gestion erreurs FR | 📋 | Backend non démarré → message FR | Haute |
| Tauri — menu Aide + mise à jour manuelle | 📋 | Lien vers release | Moyenne |
| Tauri — auto-update | 🔮 | Phase 2 | Long terme |
| Déploiement online (Dockerfile) | 📋 | FastAPI + static | Moyenne |
| Limites upload (taille, types) | 📋 | Configurable par env var | Moyenne |

---

## Ordre recommandé (prochaines sessions)

1. **🔜 Prompt formats prédéfinis** — lancer le prompt déjà préparé (6 presets de base + mode avancé)
2. **🔜 Presets SHS/NAKALA** — DOI, ORCID, ARK, W3C-DTF, langue ISO 639-1 (5 presets, juste du catalogue)
3. **🔜 Règles manquantes rapides** — `generic.required`, `generic.forbidden_chars`, `generic.case`
4. **📋 Listes avec séparateur** — `generic.list_items` + extension `allowed_values`
5. **📋 Phase B Tauri** — init + sidecar + packaging
6. **📋 Déploiement online** — Dockerfile + limites
7. **🔮 Détection auto + constructeur visuel** — quand le reste est stable
