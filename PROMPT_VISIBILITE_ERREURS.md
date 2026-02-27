# Prompt autonome — Visibilité des caractères invisibles/espaces

> Faire lire par Claude Code :
> "Lis PROMPT_VISIBILITE_ERREURS.md à la racine du repo et exécute toutes les tâches."

```
Lis CLAUDE.md pour le contexte du projet.

## Problème

Quand une cellule a un espace en fin de ligne, un caractère invisible (zero-width, NBSP), ou des espaces doubles, l'utilisateur voit le même texte que la valeur "correcte" et ne comprend pas pourquoi c'est signalé comme erreur.

## Objectif

Rendre visibles les caractères problématiques dans 3 endroits :
1. Les cellules surlignées du tableau d'aperçu (étape Configurer)
2. La liste des problèmes (étape Résultats)
3. Les tooltips sur les cellules en erreur

## Tâche 1 — Fonction JS de rendu des caractères invisibles

Dans app.js, crée une fonction `renderVisibleChars(text)` qui retourne du HTML avec les caractères invisibles remplacés par des marqueurs visuels :

### Caractères à rendre visibles :
| Caractère | Code | Rendu visuel | Classe CSS |
|---|---|---|---|
| Espace en début/fin | U+0020 | `·` (middle dot) sur fond jaune | `.char-space` |
| Espaces multiples | U+0020×2+ | `··` sur fond jaune | `.char-space-multi` |
| NBSP (espace insécable) | U+00A0 | `⍽` sur fond orange | `.char-nbsp` |
| Tabulation | U+0009 | `→` sur fond orange | `.char-tab` |
| Zero-width space | U+200B | `[ZWS]` sur fond rouge | `.char-zwsp` |
| Zero-width joiner | U+200D | `[ZWJ]` sur fond rouge | `.char-zwsp` |
| Zero-width non-joiner | U+200C | `[ZWNJ]` sur fond rouge | `.char-zwsp` |
| Soft hyphen | U+00AD | `[SHY]` sur fond orange | `.char-shy` |
| BOM | U+FEFF | `[BOM]` sur fond rouge | `.char-bom` |
| Retour ligne | U+000A | `↵` sur fond bleu clair | `.char-newline` |
| Retour chariot | U+000D | `[CR]` sur fond bleu clair | `.char-newline` |

### Logique :
```javascript
function renderVisibleChars(text) {
    if (!text) return text;
    let html = escapeHtml(text);
    
    // Zero-width characters (les plus trompeurs)
    html = html.replace(/\u200B/g, '<span class="char-zwsp">[ZWS]</span>');
    html = html.replace(/\u200D/g, '<span class="char-zwsp">[ZWJ]</span>');
    html = html.replace(/\u200C/g, '<span class="char-zwsp">[ZWNJ]</span>');
    html = html.replace(/\uFEFF/g, '<span class="char-bom">[BOM]</span>');
    html = html.replace(/\u00AD/g, '<span class="char-shy">[SHY]</span>');
    
    // NBSP
    html = html.replace(/\u00A0/g, '<span class="char-nbsp">⍽</span>');
    
    // Tabulations
    html = html.replace(/\t/g, '<span class="char-tab">→</span>');
    
    // Retours ligne
    html = html.replace(/\r/g, '<span class="char-newline">[CR]</span>');
    html = html.replace(/\n/g, '<span class="char-newline">↵</span>');
    
    // Espaces de début
    html = html.replace(/^( +)/, function(match) {
        return '<span class="char-space">' + '·'.repeat(match.length) + '</span>';
    });
    
    // Espaces de fin
    html = html.replace(/( +)$/, function(match) {
        return '<span class="char-space">' + '·'.repeat(match.length) + '</span>';
    });
    
    // Espaces multiples (au milieu)
    html = html.replace(/( {2,})/g, function(match) {
        return '<span class="char-space-multi">' + '·'.repeat(match.length) + '</span>';
    });
    
    return html;
}
```

Adapte cette logique — l'idée est là mais vérifie que l'ordre des remplacements est correct et que l'escaping HTML est fait AVANT les remplacements.

## Tâche 2 — Toggle "Afficher les caractères spéciaux"

### Dans l'étape Configurer (au-dessus du tableau d'aperçu) :

Ajoute un bouton toggle :
```html
<button id="btn-toggle-special-chars" class="btn-small btn-toggle">
  ¶ Caractères spéciaux
</button>
```

### Comportement :
1. Par défaut : désactivé (affichage normal)
2. Au clic : active le mode — toutes les cellules du tableau d'aperçu passent par `renderVisibleChars()`
3. Re-clic : désactive, revient à l'affichage normal
4. État stocké dans `state.showSpecialChars` (booléen)
5. Le bouton a un style "actif" quand le mode est on (fond coloré, bordure)

### Implémentation :
- Quand activé : parcourir toutes les <td> du tableau et remplacer textContent par innerHTML via renderVisibleChars()
- Quand désactivé : restaurer le texte original (stocker les valeurs originales dans un data-attribute ou un tableau)
- Doit se re-appliquer quand le tableau est rafraîchi (loadPreview)

## Tâche 3 — Appliquer aux cellules en erreur automatiquement

Quand une cellule est surlignée comme erreur (classes cell-error, cell-warning, cell-suspicion) :

1. Le tooltip (title) de la cellule doit utiliser une version texte des caractères visibles :
   - Au lieu de "Valeur : hello " → "Valeur : hello·· (2 espaces de fin)"
   - Pas de HTML dans le title, juste du texte avec les symboles

2. Crée une fonction `renderVisibleCharsText(text)` (version texte, sans HTML) pour les tooltips

3. Quand le mode "Caractères spéciaux" est activé, les cellules en erreur sont TOUJOURS affichées avec les caractères visibles, même quand on désactive le toggle global (les erreurs restent visibles)
   - En fait non, simplifie : le toggle s'applique à toutes les cellules uniformément

## Tâche 4 — Appliquer dans la liste des problèmes (étape Résultats)

Dans la liste des problèmes (étape 5), quand un problème concerne un caractère invisible :

1. La colonne "Valeur" dans la liste des problèmes doit afficher la valeur avec renderVisibleChars() si le mode est activé
2. Ajoute le même toggle "¶ Caractères spéciaux" en haut de l'étape Résultats aussi
3. Les deux toggles sont synchronisés (activer l'un active l'autre)

## Tâche 5 — CSS pour les marqueurs

Dans style.css :

```css
/* Caractères spéciaux rendus visibles */
.char-space {
  background: #fef9c3;
  color: #92400e;
  border-radius: 2px;
  font-size: 0.85em;
}
.char-space-multi {
  background: #fde68a;
  color: #92400e;
  border-radius: 2px;
  font-size: 0.85em;
}
.char-nbsp {
  background: #fed7aa;
  color: #9a3412;
  border-radius: 2px;
  padding: 0 2px;
  font-size: 0.85em;
}
.char-tab {
  background: #fed7aa;
  color: #9a3412;
  border-radius: 2px;
  padding: 0 2px;
}
.char-zwsp, .char-bom {
  background: #fecaca;
  color: #991b1b;
  border-radius: 2px;
  padding: 0 2px;
  font-size: 0.75em;
  font-weight: bold;
}
.char-shy {
  background: #fed7aa;
  color: #9a3412;
  border-radius: 2px;
  padding: 0 2px;
  font-size: 0.75em;
}
.char-newline {
  background: #dbeafe;
  color: #1e40af;
  border-radius: 2px;
  padding: 0 2px;
}
```

Adapte aussi pour le mode sombre (dans [data-theme="dark"]).

## Tâche 6 — Tests

Pas de tests Python nécessaires (c'est du JS pur).
Mais vérifie que :
- pytest passe (aucun changement Python)
- Le toggle fonctionne dans l'aperçu et les résultats
- Les caractères sont correctement rendus

## Règles
- Textes visibles : français (le bouton "¶ Caractères spéciaux")
- Code : anglais
- Ne modifie PAS core/ ni ui/
- CSS doit fonctionner en mode clair ET sombre
```
