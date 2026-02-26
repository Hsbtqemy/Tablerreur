# Types de contenu et formats attendus

Référence des **types** (Type de contenu) et des **formats** (Format attendu) disponibles dans l’étape Configurer, avec le lien de compatibilité pour une future restriction du menu Format selon le Type choisi.

---

## 1. Types de contenu (actuels)

| Valeur (backend) | Libellé UI |
|------------------|------------|
| *(vide)* | Aucun |
| `integer` | Nombre entier |
| `decimal` | Nombre décimal |
| `date` | Date |
| `email` | Adresse e-mail |
| `url` | URL |

**Manquant aujourd’hui** : il n’y a **pas de type « Texte »** (ni « Texte court » / « Texte long »). Les colonnes libres (titres, descriptions, etc.) ne peuvent être caractérisées que par Format attendu (ex. alphanum, letters_only) ou par longueur min/max, pas par un type sémantique.

---

## 1b. Types manquants (candidats)

| Type proposé | Formats attendus compatibles (si ajouté) |
|--------------|------------------------------------------|
| **Texte** (`text`) | `alphanum`, `letters_only`, `yes_no`, `custom` — ou aucun format imposé (texte libre). |
| **Identifiant** (`identifier`) | `doi`, `orcid`, `ark`, `issn`, `isbn`, `handle` (à ajouter), `custom`. Références canoniques (DOI, ORCID, ARK…). |
| **Adresse** (`address`) | `email`, `url`, `custom`. Moyens de contact / accès (e-mail, URL). Remplace les types actuels « Adresse e-mail » et « URL » par un seul type avec deux formats. |
| **NAKALA** (`nakala`) | Voir ci‑dessous. Regroupe tous les champs contrôlés NAKALA (vocabulaires API + formats). **Note** : si les templates NAKALA (Référence / Étendu) sont appliqués en **overlay** à l’upload, les colonnes nakala:* sont déjà préconfigurées ; un type « NAKALA » dans le menu Type de contenu devient **optionnel** (utile surtout pour mapper une colonne au nom libre vers un champ NAKALA). |
| Oui/Non, Code langue… | Voir BACKLOG.md §5 « Types de contenu manquants ». |

**Type NAKALA** : un seul type « NAKALA » dont les **formats** = les différents champs NAKALA. En choisissant Type = NAKALA et Format = (ex.) Type de ressource ou Licence, la validation et le vocabulaire (API NAKALA) s’appliquent automatiquement. **Pertinence** : une fois que le template NAKALA est appliqué en overlay (base générique + overlay), le cas d’usage principal (tableau de dépôt avec colonnes nakala:*) est couvert par le template ; le type NAKALA reste pertinent pour configurer à la main une colonne au nom quelconque comme champ NAKALA (sans passer par le template).

| Format (sous type NAKALA) | Rôle | Vocabulaire / règle |
|---------------------------|------|----------------------|
| `nakala_deposit_type` | Type de ressource (COAR) | API `vocabularies/datatypes` → `nakala.deposit_type` |
| `nakala_license` | Licence (SPDX) | API `vocabularies/licenses` → `nakala.license` |
| `nakala_language` | Code langue (ISO 639 / RFC 5646) | API `vocabularies/languages` → `nakala.language` |
| `nakala_created` | Date de création (W3C-DTF) | YYYY, YYYY-MM, YYYY-MM-DD → `nakala.created_format` |
| `nakala_creator` | Créateur (Nom, Prénom) | Format structuré → règle dédiée |

---

## 1c. Autres types de contenu envisageables

Types supplémentaires utiles en métadonnées / SHS / NAKALA, à considérer selon les besoins.

| Type envisagé | Formats possibles | Intérêt |
|---------------|-------------------|---------|
| **Langue / Code langue** (`language`) | ISO 639 (2–3 lettres), BCP 47 (fr-FR, en-GB). | Très pertinent NAKALA, multilingue ; déjà en backlog. |
| **Booléen** (`boolean`) | Oui/Non (mapping personnalisable). | Sémantique claire (vrai/faux) ; aujourd’hui seulement en format `yes_no`. |
| **Pays / Code pays** (`country`) | ISO 3166-1 alpha-2 (FR, DE). | Fréquent en métadonnées (pays de publication, affiliation). |
| **Coordonnées** (`coordinates`) | Latitude, Longitude, ou paire lat/long. | Données géo ; peut rester sous type Nombre + formats dédiés. |
| **URI** (`uri`) | URI / IRI générique (pas seulement http). | Données liées, vocabulaires ; proche d’Adresse mais plus large qu’URL. |
| **Durée / Intervalle** (`duration` ou `interval`) | Intervalle d’années (YYYY-YYYY), durée ISO 8601. | Moins prioritaire ; niche. |
| **Créateur / Personne** (`creator`) | Format structuré « Nom, Prénom ». | NAKALA ; aujourd’hui plutôt règle ou format dédié qu’un type. |

**Priorisation suggérée** : Langue et Booléen en premier (réutilisation forte) ; puis Pays ; Coordonnées et URI selon les cas d’usage.

---

**Année (YYYY)** : pas besoin d’un type séparé. Une année est une **date partielle** → Type = **Date**, Format = **Année (YYYY)**.

**Type Date = tous les formats de date** : le type « Date » regroupe les différentes formes possibles. On choisit le **format** pour imposer une seule forme (ou « Aucun » pour accepter toute date reconnue par le type) : YYYY ; YYYY-MM ; YYYY-MM-DD (ISO) ; DD/MM/YYYY (FR) ; MM/YYYY ; etc.

**Même idée pour les nombres** : on pourrait n’avoir qu’**un seul type « Nombre »** et décliner en **formats attendus** : entier, décimal, entier positif, année (YYYY), « entier ou décimal », puis latitude, longitude, etc. Aujourd’hui le menu a deux types distincts (« Nombre entier », « Nombre décimal ») ; une évolution serait de les fusionner en un type `number` avec des formats du type : `integer`, `decimal`, `positive_int`, `year`, `integer_or_decimal`, `custom`. Voir §2b et §3 (évolution).

---

## 2. Formats attendus (actuels)

### Formats généraux
| Valeur | Libellé UI |
|--------|------------|
| `year` | Année (YYYY) |
| `yes_no` | Oui / Non |
| `alphanum` | Alphanumérique |
| `letters_only` | Lettres uniquement |
| `positive_int` | Nombre entier positif |

### Identifiants (formats sous le type Identifiant — évolution proposée)
| Valeur | Libellé UI |
|--------|------------|
| `doi` | DOI |
| `orcid` | ORCID |
| `ark` | ARK |
| `issn` | ISSN |
| *(à ajouter)* | ISBN, Handle |

Références canoniques à une entité (document, personne, revue…). Type **Identifiant** = un seul type ; le format précise lequel (DOI, ORCID, ARK, etc.).

### Adresses (formats sous le type Adresse — évolution proposée)
| Valeur | Libellé UI |
|--------|------------|
| `email` | Adresse e-mail |
| `url` | URL |

Moyens de contact ou d’accès. Type **Adresse** = un seul type ; le format précise e-mail ou URL (remplace les deux types actuels « Adresse e-mail » et « URL »).

### Dates (formats sous le type Date)
| Valeur | Libellé UI | Forme acceptée |
|--------|------------|-----------------|
| `year` | Année (YYYY) | `YYYY` uniquement |
| `w3cdtf` | Date W3C-DTF | `YYYY`, `YYYY-MM` ou `YYYY-MM-DD` |
| `iso_date` | Date ISO stricte | `YYYY-MM-DD` uniquement |
| *(à ajouter)* | Date FR (JJ/MM/AAAA) | `DD/MM/YYYY` |
| *(à ajouter)* | Mois–année (MM/AAAA) | `MM/YYYY` |

Avec Type = **Date**, le validateur du type accepte déjà en « tolérant » : YYYY, YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, MM/YYYY (voir `content_type.py`). Le **format** restreint à une seule forme si on veut imposer par ex. uniquement DD/MM/YYYY ou uniquement YYYY.

### Nombres (formats sous un type Nombre — actuels / à unifier)
| Valeur | Libellé UI | Rôle |
|--------|------------|------|
| `positive_int` | Nombre entier positif | Chiffres uniquement, pas de signe |
| `year` | Année (YYYY) | 4 chiffres (souvent sous type Date) |
| *(actuellement en type)* | Nombre entier | Aujourd’hui = type `integer` |
| *(actuellement en type)* | Nombre décimal | Aujourd’hui = type `decimal` |
| *(à ajouter)* | Entier ou décimal | Les deux acceptés |
| *(à ajouter)* | Latitude / Longitude | Bornes -90/90, -180/180 |

Si on adopte **un seul type Nombre** : ces éléments deviennent des **formats** (entier, décimal, entier positif, année, etc.), comme pour Date.

### Codes & référentiels
| Valeur | Libellé UI |
|--------|------------|
| `lang_iso639` | Langue ISO 639 (fr, en, de…) |

### Avancé
| Valeur | Libellé UI |
|--------|------------|
| `custom` | Personnalisé (regex)… |

---

## 3. Compatibilité type → formats

Quand un **Type de contenu** est choisi, seuls les **formats** listés ci‑dessous sont considérés comme compatibles (pour restreindre le menu « Format attendu »).

| Type de contenu | Formats attendus compatibles |
|-----------------|------------------------------|
| **Aucun** | Tous les formats (aucune restriction). |
| **Nombre entier** (`integer`) *(actuel)* | `year`, `positive_int`, `custom`. |
| **Nombre décimal** (`decimal`) *(actuel)* | `custom`. |
| **Nombre** (`number`) *(évolution proposée : un seul type)* | `integer`, `decimal`, `positive_int`, `year`, `integer_or_decimal`, latitude/longitude (à ajouter), `custom`. |
| **Date** (`date`) | `year` (YYYY), `w3cdtf` (YYYY / YYYY-MM / YYYY-MM-DD), `iso_date` (YYYY-MM-DD), puis à ajouter : date FR (DD/MM/YYYY), mois–année (MM/YYYY), `custom`. |
| **Adresse e-mail** (`email`) *(actuel)* | `custom`. |
| **URL** (`url`) *(actuel)* | `custom`. |
| **Identifiant** (`identifier`) *(évolution proposée)* | `doi`, `orcid`, `ark`, `issn`, `isbn`, `handle` (à ajouter), `custom`. |
| **Adresse** (`address`) *(évolution proposée)* | `email`, `url`, `custom`. Remplace les types email et url par un seul type avec deux formats. |
| **NAKALA** (`nakala`) *(évolution proposée)* | `nakala_deposit_type`, `nakala_license`, `nakala_language`, `nakala_created`, `nakala_creator`. Tous les champs contrôlés NAKALA ; validation + vocabulaires API selon le format. |

Formats **sans type dédié** (affichés uniquement quand Type = Aucun, ou à rattacher à de futurs types) :
- `alphanum`, `letters_only`, `yes_no` — (futur type **Texte**)
- `lang_iso639` — (futur type « Code langue » ?)

---

## 4. Usage

- **Implémentation** : pour la fonctionnalité « Restreindre les formats attendus selon le type choisi » (backlog §5), utiliser cette table comme source de vérité (ex. structure JS ou attributs `data-` dans le HTML).
- **Évolution** : ajout de types (Texte, Identifiant, Adresse, NAKALA, Code langue) → §1b et §3. Fusions : **integer + decimal → Nombre** ; **email + url → Adresse** ; **DOI / ORCID / ARK / ISSN → Identifiant**. **Type NAKALA** : un type dédié dont les formats = champs NAKALA (type ressource, licence, langue, date créée, créateur), avec validation et vocabulaires API.
