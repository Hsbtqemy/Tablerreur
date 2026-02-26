# NAKALA — Fiche validation / formats acceptés

> Référence pour la validation des métadonnées selon le modèle de description NAKALA : **5 propriétés NAKALA obligatoires (nkl)** + **Dublin Core Terms (dcterms)** + **relations DataCite (RelationType)**.  
> Les listes fermées (« termes acceptés ») doivent idéalement être récupérées via l’API `/vocabularies/*` plutôt que codées en dur.

---

## 1. Les 3 familles de « termes acceptés » dans NAKALA

| Famille | Préfixe / source | Rôle |
|--------|-------------------|------|
| **Propriétés NAKALA obligatoires** | `nakala:` / `nkl:` | 5 champs bloquants pour une donnée |
| **Propriétés Dublin Core qualifié** | `dcterms:` | Champs complémentaires et avancés ; certaines valeurs typées via encodage (W3CDTF, URI, etc.) |
| **Relations DataCite** | RelationType | Liste fermée pour les types de relation (Cites, IsCitedBy, IsPartOf, HasPart, etc.) |

---

## 2. Métadonnées obligatoires pour une DONNÉE (et formats)

| Champ UI | Propriété | Cardinalité | Valeurs acceptées | Format attendu / contraintes |
|----------|-----------|-------------|-------------------|------------------------------|
| **Type de dépôt** | `nakala:type` | 1 | Liste fermée (COAR Resource Types) | URI COAR (ex. `http://purl.org/coar/resource_type/...`). À récupérer via **API** `/vocabularies/datatypes`. |
| **Titre** | `nakala:title` | n | Texte libre | Titre(s) en texte libre. Langue à renseigner pour chaque titre (champ « langue de la métadonnée »). |
| **Auteurs** | `nakala:creator` | n | Format contraint | « Nom, Prénom » (ORCID optionnel). Si pas « Nom/Prénom » (organisation, auteur inconnu…) → utiliser « Anonyme » et renseigner plutôt `dcterms:creator` / `dcterms:contributor` en texte libre. |
| **Date de création** | `nakala:created` | 1 | W3C-DTF (restreint) | Uniquement : `YYYY-MM-DD` ou `YYYY-MM` ou `YYYY`. Sinon cocher « Inconnue ». |
| **Licence** | `nakala:license` | 1 | Liste fermée | Sélection dans le vocabulaire de licences (CC, Etalab, etc.). À valider via **API** `/vocabularies/licenses`. |

**Règle d’implémentation :** ces 5 champs sont **bloquants (erreur)** si manquants ou invalides.

---

## 3. Métadonnées « complémentaires » fortement recommandées

| Champ | Propriété | Valeur | Note |
|-------|-----------|--------|------|
| **Description** | `dcterms:description` (multivaluée) | Texte libre | Langue recommandée (champ « langue de la métadonnée »). |
| **Mots-clés** | `dcterms:subject` (multivaluée) | Label libre (avec langue) **ou** valeur typée | Encodages possibles : `dcterms:LCSH`, `dcterms:TGN`, ou `dcterms:URI`. |
| **Langues** (contenu des fichiers) | `dcterms:language` (multivaluée) | Liste fermée RFC5646 | Via **API** `/vocabularies/languages`. |

---

## 4. Obtenir « tous les termes acceptés » sans les lister à la main

Pour ne pas recopier à la main toutes les propriétés Dublin Core, l’approche robuste consiste à s’appuyer sur l’API NAKALA :

| Usage | Endpoint | Détails |
|-------|----------|---------|
| **Propriétés de métadonnées acceptées** | `GET /vocabularies/properties` | Liste des propriétés autorisées. |
| **Types/encodages par propriété** | `GET /vocabularies/properties/details` | Types/encodages autorisés par propriété. |
| **Encodages (types) acceptés** | `GET /vocabularies/metadatatypes` | Liste des types de métadonnées (W3CDTF, URI, LCSH, etc.). |
| **Détails encodages** | `GET /vocabularies/metadatatypes/details` | Détails par type. |

**Règle d’or** (fiche NAKALA d’origine) : dans l’outil qui dépose les métadonnées vers l’API (« pusher »), valider **propriété ∈ properties** et **type/encoding ∈ metadatatypes**, sinon erreur « métadonnée non acceptée ». *Tablerreur ne fait pas ce dépôt : il valide les colonnes en amont ; les endpoints properties/metadatatypes peuvent toutefois servir à enrichir cette validation.*

### Autres vocabulaires utiles (API)

| Vocabulaire | Endpoint | Usage |
|-------------|----------|--------|
| Types de dépôt (COAR) | `GET /vocabularies/datatypes` | `nakala:type` (liste d’URIs COAR). |
| Licences | `GET /vocabularies/licenses` | `nakala:license`. |
| Langues | `GET /vocabularies/languages?limit=10000` | `dcterms:language`, codes RFC5646. |
| Types DCMI | `GET /vocabularies/dcmitypes` | `dcterms:type` avec encodage DCMIType. |
| Codes pays | `GET /vocabularies/countryCodes` | dcterms:spatial / subject (ISO3166). |
| LCSH | `GET /vocabularies/lcsh` | dcterms:subject (Library of Congress). |
| Statuts donnée / collection | `GET /vocabularies/dataStatuses`, `GET /vocabularies/collectionStatuses` | Statut donnée ; pour collections : privé/public. |

**Note :** dans le projet Tablerreur, l’endpoint utilisé pour le type de ressource est **`/vocabularies/datatypes`** (vérifié en 2026 ; `depositTypes` peut désigner le même concept selon la doc).

---

## 5. Encodages (champ « Type ») et formats exacts acceptés

La **propriété** indique « ce que c’est », l’**encodage** indique « comment la valeur est encodée ». Par défaut : string (texte).

| Encodage | Propriété typique | Valeur / contraintes |
|----------|-------------------|----------------------|
| **dcterms:DCMIType** | `dcterms:type` (obligatoire si ce type) | 1 parmi 12 : Collection, Dataset, Event, Image, InteractiveResource, MovingImage, PhysicalObject, Service, Software, Sound, StillImage, Text. |
| **dcterms:LCSH** | `dcterms:subject` | Identifiant LCSH uniquement (ex. `sh85145114`), pas de label ni URI. |
| **dcterms:TGN** | `dcterms:subject` ou `dcterms:spatial` | Identifiant TGN uniquement (souvent numérique), sans label ni URI. |
| **dcterms:Box** | `dcterms:spatial` | Chaîne structurée `;` : requis `northlimit`, `southlimit`, `eastlimit`, `westlimit` ; optionnels `uplimit`, `downlimit`, `name`, `units`, `zunits`, `projection`. Latitudes [-90, +90], longitudes [-180, 180]. `units` : uniquement `"signed decimal degrees"` ; `projection` : uniquement `"WGS84"`. Ex. : `northlimit=48.9354; southlimit=47.2479; westlimit=-4.8504; eastlimit=-0.9722`. |
| **dcterms:ISO3166** | `dcterms:spatial` ou `dcterms:subject` | Code pays ISO 3166 alpha-2 (2 lettres), ex. FR, IT. |
| **dcterms:RFC5646** | `dcterms:language` ou `dcterms:subject` | Tag RFC5646 (ex. fr, en, it). Liste : `/vocabularies/languages?limit=10000`. |
| **dcterms:Period** | `dcterms:temporal`, `dcterms:date` (et sous-propriétés) | Chaîne structurée : requis `start`, `end` ; optionnel `name`. Années ≥ 4 chiffres ; années négatives permises ; `start < end`. Ex. : `name=Paléolithique; start=-300000; end=-40000`. |
| **dcterms:Point** | `dcterms:spatial` | Chaîne structurée : requis `east`, `north` ; optionnels `elevation`, `name`, `units`, `projection`, `zunits`. `east` ∈ [-180, 180], `north` ∈ [-90, 90] ; `units` : `"signed decimal degrees"`, `projection` : `"WGS84"`, `zunits` : `"metres"`. Ex. : `east=-2.83333; north=48.16667; name=Bretagne`. |
| **dcterms:URI** | Toute `dcterms:*` si valeur = lien | URI/URL seule, pas de texte autour. |
| **dcterms:W3CDTF** | `dcterms:date` + sous-propriétés, `dcterms:temporal`, `dcterms:coverage`, `dcterms:subject` | Date/heure W3CDTF : `YYYY` \| `YYYY-MM` \| `YYYY-MM-DD` \| datetime (ex. `1999-09-25T16:40+10:00`) ; années négatives possibles. |

---

## 6. Relations DataCite (RelationType)

Pour la zone « Relations vers d’autres données », le **type de relation** doit être un **RelationType DataCite** (liste fermée).

Exemples : Cites / IsCitedBy, IsSupplementTo / IsSupplementedBy, IsPartOf / HasPart, IsDescribedBy, IsIdenticalTo, IsDerivedFrom, IsPublishedIn, etc.

**Règle :** valider côté programme que `relationType ∈ liste DataCite` (casse et espaces conformes).

---

## 7. Spécificité COLLECTIONS

Pour la description des **collections**, le même modèle s’applique avec des obligatoires réduits :

| Champ | Valeurs | API |
|-------|---------|-----|
| **Statut de collection** | Privé / public (liste fermée) | `/vocabularies/collectionStatuses` |
| **Titre** | Texte libre (multilingue possible) | — |

---

## 8. Template : sélection + formats attendus

**Objectif :** que chaque champ NAKALA/dcterms ait, côté UI, à la fois une **sélection** (liste déroulante quand les valeurs sont contrôlées) et le **format attendu** (validation : W3CDTF, « Nom, Prénom », URI COAR, etc.).

| Mécanisme | Rôle |
|-----------|------|
| **Template (YAML)** | Pour chaque colonne : `kind` (controlled, structured, free_text_short…), `allowed_values` (optionnel), `allowed_values_locked`, `regex` ou règle dédiée, `rule_overrides`. Définit **formats attendus** (règles + regex) et, pour certaines colonnes, la **liste de valeurs** (ex. types COAR en dur dans le template). |
| **API `/vocabularies/*`** | Fournit les listes à jour (types COAR, licences, langues, etc.). L’UI peut **charger un vocabulaire** (ex. « Licences NAKALA ») et remplir `allowed_values` à partir de l’API, au lieu de tout mettre dans le template. |
| **Combinaison template + API** | Le template indique *quelles* colonnes sont contrôlées et *quel* format/règle appliquer ; pour la **sélection**, soit le template contient déjà `allowed_values` (ex. types COAR en fallback), soit l’utilisateur (ou le template) déclare la **source** du vocabulaire (ex. `nakala_vocabulary: licenses`) et l’UI charge les valeurs via l’API. |

**Aujourd’hui dans Tablerreur :**

- **Type de dépôt (`nakala:type`)** : template = liste COAR en dur (29 URIs) + règle `nakala.deposit_type` → **sélection** (dropdown) + **format** (URI COAR) ✅  
- **Licence (`nakala:license`)** : template = pas de liste (trop longue) ; règle `nakala.license` → **format** (SPDX) ✅ ; **sélection** = chargement manuel dans l’UI via « Charger le vocabulaire NAKALA » (licenses) ✅  
- **Langue (`dcterms:language`)** : idem, règle `nakala.language` + sélection possible via vocabulaire « languages » en UI.  
- **Date (`nakala:created`)** : pas de sélection (saisie libre) ; **format** = W3C-DTF restreint (YYYY, YYYY-MM, YYYY-MM-DD) via règle `nakala.created_format` ✅  
- **Créateur (`nakala:creator`)** : pas de sélection ; **format** = « Nom, Prénom » (regex) ✅  
- **Titre (`nakala:title`)** : texte libre, pas de liste fermée.

**Pour « tout avoir en sélection avec les formats attendus » :**

1. **Champs à liste fermée** (type, licence, langue, puis plus tard RelationType, statut collection) : le template peut soit inclure `allowed_values`, soit référencer une **source de vocabulaire** (ex. `vocabulary_source: datatypes | licenses | languages`) pour que l’UI préremplisse la sélection au chargement du template (sans action manuelle). Les **formats attendus** sont déjà portés par les règles et options du template (regex, `nakala.created_format`, etc.).  
2. **Champs à format contraint sans sélection** (date, créateur) : le template garde la règle + regex ; l’UI affiche l’aide/format attendu, pas de dropdown.  
3. **Évolution possible** : dans le template, pour chaque colonne contrôlée, un champ du type `vocabulary: licenses` ou `nakala_vocabulary: languages` permettrait de lier automatiquement la colonne au bon endpoint et d’afficher la sélection dès l’application du template (voir BACKLOG : « Appliquer le type selon le champ dcterms/nakala », « Template depuis l’API NAKALA »).

En résumé : **oui**, le template (éventuellement complété par une source de vocabulaire et le chargement API) peut fournir à la fois la **sélection** (liste fermée) et le **format attendu** (règles + encodages) pour tous les champs NAKALA ; aujourd’hui une partie est déjà en place (type = liste dans le template, licence/langue = chargement manuel du vocabulaire), le reste est améliorable (préremplissage automatique des listes depuis l’API selon le champ, RelationType, collections).

---

## 9. Autres éléments importants

### 9.1 Messages d’erreur en français

Toute l’interface utilisateur doit être en **français** (projet Tablerreur). Les règles NAKALA (`nakala_rules.py`) renvoient aujourd’hui des **messages et suggestions en anglais** (ex. « Invalid NAKALA date format », « Unknown NAKALA deposit type », « Use a COAR deposit type from… »). Il faut les traduire ou passer par un système de clés (ex. `fr.json`) pour afficher les messages en français dans l’UI web et les exports.

### 9.2 Valeurs spéciales « Inconnue » et « Anonyme »

- **Date (`nakala:created`)** : la fiche NAKALA indique « Sinon cocher ‹ Inconnue › » quand la date n’est pas connue. Aujourd’hui la règle n’accepte que YYYY / YYYY-MM / YYYY-MM-DD ; une valeur comme « Inconnue » (ou un code convenu) devrait être acceptée sans erreur, ou documentée comme valeur réservée à gérer (ex. exclue de la validation, ou mappée côté export).
- **Créateur (`nakala:creator`)** : la fiche indique d’utiliser « Anonyme » si pas de format « Nom, Prénom » (organisation, auteur inconnu) et de renseigner `dcterms:creator` / `dcterms:contributor` en texte libre. Le template utilise une regex « Nom, Prénom » qui **ne matche pas** « Anonyme ». Il faut soit accepter « Anonyme » comme valeur valide (exception dans la règle ou regex), soit le documenter et l’ajouter au template.

### 9.3 Langue de la métadonnée (titres, descriptions)

Pour les champs multivalués (titre, description), la fiche recommande de **renseigner la langue pour chaque valeur** (champ « langue de la métadonnée »). Dans Tablerreur, le template Extended prévoit des colonnes multilingues (`nakala:title_*`, `dcterms:description_*`) ; le lien explicite « valeur ↔ langue » (ex. titre_fr, titre_en) est couvert par le nom de colonne. Pour aller plus loin : documenter ou supporter un schéma où chaque titre/description est accompagné d’un code langue (colonne jumelle ou structure dédiée).

### 9.4 Type COAR vs type DCMI

- **`nakala:type`** (obligatoire) : vocabulaire **COAR Resource Types** (URIs, ex. `http://purl.org/coar/resource_type/c_18cf`) → API `/vocabularies/datatypes`.
- **`dcterms:type`** (optionnel) : vocabulaire **DCMI Type** (12 valeurs : Collection, Dataset, Image, Text, etc.) → API `/vocabularies/dcmitypes`.

Ce sont **deux vocabulaires différents**. Ne pas confondre dans les templates ni dans l’UI (deux champs distincts si les deux sont utilisés).

### 9.5 Références d’URL dans les messages

Les suggestions des règles NAKALA doivent pointer vers l’endpoint effectivement utilisé : **`/vocabularies/datatypes`** (et non `deposittypes`). *Corrigé dans le code (nakala_rules.py).*

### 9.6 Comportement hors ligne

Quand le réseau est indisponible : les règles qui s’appuient sur `NakalaClient` (deposit_type, license, language) **ne font pas d’erreur** (retour liste vide → skip). Pour **type**, le template fournit une liste de fallback (29 URIs COAR) donc la sélection reste utilisable. Pour **licence** et **langue**, pas de liste dans le template → pas de dropdown hors ligne ; à documenter pour l’utilisateur (ex. « Connectez-vous pour charger les listes de licences et langues »).

---

## Alignement avec Tablerreur

- **Règles actuelles** : `nakala.deposit_type`, `nakala.license`, `nakala.created_format`, `nakala.language` ; vocabulaires chargés depuis `datatypes`, `licenses`, `languages` (voir `nakala_api.py` et `docs/nakala.md`).
- **À prévoir** : utilisation de `/vocabularies/properties` et `/vocabularies/metadatatypes` pour valider propriété et encodage ; liste RelationType DataCite pour les relations ; encodages structurés (Box, Point, Period) si colonnes dédiées ; support collections (collectionStatuses). Voir BACKLOG.md.
