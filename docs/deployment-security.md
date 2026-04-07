# Déploiement et sécurité — Tablerreur

Ce document résume les **hypothèses de menace** et les **bonnes pratiques** pour l’API FastAPI (usage en ligne ou sur un serveur), en complément du backlog d’audit (`AUD-P0-01`).

## Modèle prévu

### Application desktop (Tauri)

- Le **sidecar Python** est lancé par l’app native ; le navigateur embarqué pointe vers **`http://127.0.0.1:{port}`** (port dans une plage locale).
- **Pas d’authentification** sur ce flux : le risque principal est **local** (accès au poste utilisateur). Le **menu Quitter** et la **fermeture de fenêtre** terminent le sidecar pour éviter un processus orphelin (`AUD-P0-03`).

### Serveur (Docker / réseau)

- L’**image Docker** lance `uvicorn` sur **`0.0.0.0`** — tout client qui peut joindre le **port** peut utiliser l’API.
- **Attention** : le fichier `docker-compose.yml` du dépôt fixe parfois `TABLERREUR_CORS_ORIGINS=*` ; à **resserrer** si l’API est exposée au-delà d’un réseau de confiance.

## Points critiques

1. **Pas d’authentification** : l’accès à un jeu de données repose sur la connaissance du **`job_id`** (UUID). Ne **pas** exposer l’API sur Internet **sans** couche d’authentification (proxy avec SSO, JWT, clé API, VPN, etc.) si les fichiers sont sensibles.

2. **CORS** : régler `TABLERREUR_CORS_ORIGINS` sur les **origines autorisées** (pas `*` en production si des navigateurs distants ne doivent pas appeler l’API).

3. **Données temporaires** : les jobs et fichiers résident en clair sous des répertoires temporaires jusqu’à expiration (TTL). Adapter la **durée de vie** et les **droits disque** au contexte (mono-utilisateur vs multi-tenant).

4. **Limites d’upload** : `TABLERREUR_MAX_UPLOAD_MB` s’applique au téléversement principal et, pour **Mapala**, à **chaque** fichier (template et source) — lecture **par fichier** avec réponse **413** si dépassement (`AUD-P0-02`, `mapala_routes.py`). Valeur invalide en variable d’environnement : repli sur **50** Mo (Mapala) ; minimum effectif **1** Mo.

5. **Documentation OpenAPI** : en production, FastAPI expose en général **`/docs`** et **`/openapi.json`** — surface d’information pour un attaquant ; à désactiver ou restreindre si l’API est publique (voir backlog **AUD-P1-04**).

## Références

- Variables d’environnement : voir `CLAUDE.md` et `spreadsheet_qa/web/app.py`.
- Image Docker : `Dockerfile`, `docker-compose.yml`.
