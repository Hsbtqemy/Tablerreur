# Parité fonctionnelle : Qt Desktop vs Interface Web

## Légende

| Symbole | Signification |
|---------|---------------|
| ✅ | Disponible dans les deux |
| ❌ | Qt seulement (pas encore dans le web) |
| 🆕 | Web seulement (fonctionnalité nouvelle) |

---

## 1. Chargement / Import

| Fonctionnalité | Qt | Web |
|---|---|---|
| CSV / XLSX | ✅ | ✅ |
| Encodage auto-détecté | ✅ | ✅ |
| Délimiteur auto-détecté | ✅ | ✅ |
| Ligne d'en-tête configurable | ✅ | ✅ |
| Sélection template à l'import | ✅ | ✅ (par ID) |

---

## 2. Templates

| Fonctionnalité | Qt | Web |
|---|---|---|
| Bibliothèque de templates | ✅ | ❌ |
| Éditeur visuel de template | ✅ | ❌ |
| Overlay / surcharge de template | ✅ | ✅ (par ID) |

---

## 3. Correctifs

| Fonctionnalité | Qt | Web |
|---|---|---|
| 7 types de corrections hygiènes | ✅ | ✅ |
| Aperçu avant application | ✅ | ✅ |
| Annuler / Rétablir | ✅ | ❌ |
| Filtrer par colonnes | ✅ | ✅ |

---

## 4. Validation

| Fonctionnalité | Qt | Web |
|---|---|---|
| Moteur de règles complet | ✅ | ✅ |
| Résumé (erreurs / avert. / susp.) | ✅ | ✅ |

---

## 5. Résultats & Problèmes

| Fonctionnalité | Qt | Web |
|---|---|---|
| Tableau filtrable par sévérité | ✅ | ✅ |
| Filtre par colonne | ✅ | ✅ |
| Navigation vers la cellule | ✅ | ❌ |
| Ignorer / Exclure un problème | ✅ | ❌ |
| Pagination | ❌ | 🆕 |

---

## 6. Exports

| Fonctionnalité | Qt | Web |
|---|---|---|
| XLSX nettoyé | ✅ | ✅ |
| CSV nettoyé (UTF-8, ;) | ✅ | ✅ |
| Rapport TXT FR | ✅ | ✅ |
| problèmes.csv FR | ✅ | ✅ |

---

## 7. Projet & Historique

| Fonctionnalité | Qt | Web |
|---|---|---|
| Ouvrir / Sauvegarder projet | ✅ | ❌ |
| Historique des patches | ✅ | ❌ |
| Exceptions persistantes | ✅ | ❌ |

---

## Divers

| Fonctionnalité | Qt | Web |
|---|---|---|
| Mode sombre (stylesheet) | ✅ | ❌ |
| Accès depuis navigateur distant | ❌ | 🆕 |

---

## Priorités de convergence (Phase C)

Les fonctionnalités suivantes sont présentes dans Qt mais absentes du web et représentent la priorité pour la Phase C :

1. **Bibliothèque et éditeur de templates** — permettre à l'utilisateur de parcourir, créer et modifier des templates depuis l'interface web
2. **Ignorer / Exclure un problème** — actions par problème dans le tableau de résultats
3. **Navigation vers la cellule** — clic sur un problème → mise en évidence dans un aperçu du tableau
4. **Annuler / Rétablir** — historique des correctifs pour la session web
5. **Gestion de projet** — persistance des patches et exceptions entre sessions
6. **Mode sombre** — thème sombre via CSS (variable CSS ou classe sur `<body>`)
