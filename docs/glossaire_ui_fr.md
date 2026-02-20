# Glossaire UI — Tablerreur (français)

Ce document est la **source de vérité** pour la terminologie de l'interface utilisateur de Tablerreur.
Il s'applique à la fois à l'application de bureau (PySide6) et à l'application web (FastAPI).

Toute nouvelle chaîne ajoutée à l'interface doit s'appuyer sur les termes définis ici.
Pour ajouter ou modifier une étiquette, mettre à jour ce fichier ET le fichier `src/spreadsheet_qa/ui/i18n.py` (bureau) et/ou `src/spreadsheet_qa/web/static/fr.json` (web).

---

## 1. Concepts métier

| Terme français | Terme technique (interne) | Notes |
|---|---|---|
| Problème | Issue | Résultat d'une règle de validation |
| Correctif | Fix / Patch | Modification appliquée à une cellule |
| Modèle (de validation) | Template | Fichier YAML de configuration des règles |
| Modèle de base | Generic template | Niveau de validation de base (ex. Générique par défaut) |
| Surcouche | Overlay | Modèle complémentaire appliqué par-dessus le modèle de base |
| Règle | Rule | Algorithme de validation individuel |
| Surcharge de règle | Rule override | Configuration spécifique à une colonne |

---

## 2. Sévérité des problèmes

| Terme français | Valeur interne | Couleur |
|---|---|---|
| Erreur | `ERROR` | Rouge |
| Avertissement | `WARNING` | Ambre |
| Suspicion | `SUSPICION` | Bleu/violet |

---

## 3. Statut des problèmes

| Terme français | Valeur interne | Description |
|---|---|---|
| Ouvert | `OPEN` | Problème non résolu |
| Corrigé | `FIXED` | Correctif appliqué |
| Ignoré | `IGNORED` | Supprimé de la vue (temporaire) |
| Excepté | `EXCEPTED` | Exception persistante (enregistrée dans exceptions.yml) |

---

## 4. Types de colonnes (Profil)

| Terme français | Valeur interne | Description |
|---|---|---|
| Texte court | `free_text_short` | Texte libre, une ligne |
| Texte long | `free_text_long` | Texte libre, multilignes attendu |
| Valeurs contrôlées | `controlled` | Liste fermée de valeurs autorisées |
| Structuré | `structured` | Format strict (URI, date, ORCID…) |
| Liste (|) | `list` | Valeurs multiples séparées par `|` |

---

## 5. Préréglages de colonne

| Terme français | Valeur interne |
|---|---|
| (aucun) | `(none)` |
| Date (W3C DTF / AAAA-MM-JJ) | `w3c_dtf_date` |
| URI | `uri` |
| Courriel | `email` |
| ORCID | `orcid` |
| Nom du créateur | `creator_name` |
| Regex personnalisée | `custom_regex` |

---

## 6. Correctifs typiques (Correctifs d'hygiène)

| Étiquette française | Description |
|---|---|
| Remplacer la correspondance exacte | Rechercher/remplacer un texte exact |
| Supprimer les espaces en début et fin | `str.strip()` |
| Réduire les espaces multiples | `re.sub(r"  +", " ", …)` |
| Normaliser l'Unicode | Remplacement des guillemets courbes, tirets, etc. (NFC) |
| Supprimer les caractères invisibles | Suppression des caractères de largeur nulle (U+200B, etc.) |
| Remplacer les espaces insécables (NBSP) | Remplacement de U+00A0 par espace ordinaire |
| Normaliser les retours à la ligne | Normalisation des fins de ligne (`\r\n` → `\n`) |

---

## 7. Actions principales

| Terme français | Raccourci |
|---|---|
| Ouvrir un fichier | Ctrl+O |
| Valider | Ctrl+Maj+V |
| Chercher & Corriger | Ctrl+F |
| Annuler | Ctrl+Z |
| Rétablir | Ctrl+Maj+Z |
| Exporter | Ctrl+E |
| Panneau des problèmes | Ctrl+I |

---

## 8. Métadonnées de fichier

| Terme français | Terme technique |
|---|---|
| Encodage | Encoding (UTF-8, latin-1…) |
| Délimiteur | Delimiter (`;`, `,`, `\t`, `|`) |
| Feuille | Sheet (XLSX uniquement) |
| Ligne d'en-tête | Header row (index 0-based en interne, 1-based dans l'UI) |

---

## 9. Modèles intégrés

| Nom affiché | Identifiant interne | Description |
|---|---|---|
| Générique — Défaut | `generic_default` | Validation permissive de base |
| Générique — Strict | `generic_strict` | Seuils plus stricts |
| NAKALA — Référence | `nakala_baseline` | Règles spécifiques NAKALA |
| NAKALA — Étendu | `nakala_extended` | Validation NAKALA étendue |

---

## 10. Exports

| Terme français | Extension | Description |
|---|---|---|
| Tableur nettoyé | `.xlsx` / `.csv` | Données corrigées |
| Rapport de validation | `.txt` | Résumé lisible |
| Liste des problèmes | `.csv` | Export structuré des problèmes |

---

## 11. Pour les mainteneurs — Ajouter/modifier une étiquette

1. Trouver ou créer la clé appropriée dans `src/spreadsheet_qa/ui/i18n.py` (bureau) et/ou `src/spreadsheet_qa/web/static/fr.json` (web).
2. Respecter la convention de nommage des clés : `domaine.sous_domaine.nom` (ex. `issues.filter.severity`).
3. Mettre à jour ce glossaire si le terme est nouveau ou s'il modifie un terme existant.
4. Lancer le script de vérification : `python scripts/check_english_strings.py` pour détecter d'éventuels termes anglais résiduels.
