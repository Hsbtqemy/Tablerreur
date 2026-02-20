# Backlog — Version Tauri (Tablerreur)

Points à traiter pour la version desktop Tauri (ou l’UI web partagée).  
À prioriser selon la phase de migration.

---

## UX / Visibilité des erreurs

### Rendre les erreurs visibles au moment de la comparaison

**Problème :** Aujourd’hui, des erreurs comme un espace en fin de ligne ou un caractère invisible ne se voient pas dans la cellule : l’utilisateur voit le même texte que la valeur “correcte” et ne comprend pas ce qui est signalé.

**Souhait :** Au moment où une issue est affichée (ou lors du survol / focus sur la cellule en erreur), rendre visibles les éléments en cause, par exemple :

- **Espaces de fin / début** : les afficher clairement (symbole visible, surlignage, ou représentation type “·” / “¶”).
- **Caractères invisibles** (zero-width, NBSP, etc.) : les afficher sous forme de symbole ou de code (ex. U+200B) ou les surligner.
- **Doublons d’espaces** : les distinguer visuellement (surlignage ou marqueur).

**Contexte :** Applicable à la vue “comparaison” ou détail d’issue (diff original vs suggestion), et idéalement dans la cellule elle-même quand elle est en erreur (tooltip, surlignage, ou mode “afficher les caractères spéciaux” pour la cellule/colonne).

**Critères d’acceptation (exemples) :**

- Pour une issue “leading/trailing space”, l’utilisateur voit où sont les espaces (début/fin).
- Pour une issue “invisible chars”, l’utilisateur voit quel caractère est en cause (ou sa position).
- Le comportement est cohérent entre liste d’issues et vue tableau (cellule en erreur).

---

*Ajouter les prochaines entrées backlog ci-dessous.*
