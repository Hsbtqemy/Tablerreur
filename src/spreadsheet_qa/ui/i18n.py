"""i18n — French-first UI translation layer for Tablerreur.

Usage::

    from spreadsheet_qa.ui.i18n import t, severity_label, status_label

    # Simple lookup
    title = t("app.title")

    # With format kwargs
    msg = t("status.loaded", name="data.csv", rows=100, cols=5)

    # Severity / status display
    label = severity_label("ERROR")   # → "Erreur"
    label = status_label("IGNORED")   # → "Ignoré"

Only French is currently supported. The architecture allows adding other
languages later by swapping the active dictionary.

See also: docs/glossaire_ui_fr.md for the full terminology reference.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# French string dictionary
# ---------------------------------------------------------------------------

FR: dict[str, str] = {
    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    "app.title": "Tablerreur — Contrôle qualité tableurs",
    "app.ready": "Prêt. Ouvrez un fichier pour commencer.",

    # ------------------------------------------------------------------
    # Toolbar / Actions
    # ------------------------------------------------------------------
    "action.open": "Ouvrir…",
    "action.open.tooltip": "Ouvrir un fichier CSV ou XLSX",
    "action.validate": "Valider",
    "action.validate.tooltip": "Lancer toutes les règles de validation",
    "action.findfix": "Chercher && Corriger",
    "action.findfix.tooltip": "Ouvrir le tiroir Chercher && Corriger",
    "action.undo": "Annuler",
    "action.redo": "Rétablir",
    "action.undo.tooltip": "Annuler : {desc}",
    "action.redo.tooltip": "Rétablir : {desc}",
    "action.templates": "Modèles…",
    "action.templates.tooltip": "Ouvrir la bibliothèque de modèles",
    "action.export": "Exporter…",
    "action.export.tooltip": "Exporter le fichier nettoyé et les rapports",
    "action.issues_panel": "Panneau des problèmes",

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------
    "menu.file": "&Fichier",
    "menu.file.open_project": "Ouvrir un projet…",
    "menu.file.save_project": "Enregistrer le projet sous…",
    "menu.file.quit": "Quitter",
    "menu.edit": "&Édition",
    "menu.view": "&Affichage",
    "menu.validate": "&Valider",
    "menu.tools": "&Outils",

    # ------------------------------------------------------------------
    # Dock widgets
    # ------------------------------------------------------------------
    "dock.issues": "Problèmes",
    "dock.findfix": "Chercher && Corriger",

    # ------------------------------------------------------------------
    # Status bar messages
    # ------------------------------------------------------------------
    "status.validating": "Validation en cours…",
    "status.validation_done": "Validation : {e} erreur(s), {w} avertissement(s), {s} suspicion(s)",
    "status.loaded": "Chargé : {name}  ({rows} ligne(s) × {cols} colonne(s))",
    "status.export_done": "Export terminé → {path}",
    "status.template_changed": "Modèle : {id}{overlay}",
    "status.project_opened": "Projet ouvert : {name}",
    "status.project_saved": "Projet enregistré : {path}",

    # ------------------------------------------------------------------
    # Column context menu (right-click on column header)
    # ------------------------------------------------------------------
    "col_menu.title": "Colonne : {name}",
    "col_menu.set_kind": "Définir le type",
    "col_menu.required": "Obligatoire",
    "col_menu.unique": "Unique",
    "col_menu.multiline": "Multiligne autorisé",
    "col_menu.edit_template": "Éditer dans l'éditeur de modèles…",

    # ------------------------------------------------------------------
    # Column kind display names
    # ------------------------------------------------------------------
    "kind.free_text_short": "Texte court",
    "kind.free_text_long": "Texte long",
    "kind.controlled": "Valeurs contrôlées",
    "kind.structured": "Structuré",
    "kind.list": "Liste (|)",

    # ------------------------------------------------------------------
    # Severity labels
    # ------------------------------------------------------------------
    "severity.ERROR": "Erreur",
    "severity.WARNING": "Avertissement",
    "severity.SUSPICION": "Suspicion",
    "severity.all": "Toutes les sévérités",

    # ------------------------------------------------------------------
    # Issue status labels
    # ------------------------------------------------------------------
    "status.OPEN": "Ouvert",
    "status.FIXED": "Corrigé",
    "status.IGNORED": "Ignoré",
    "status.EXCEPTED": "Excepté",
    "status.all": "Tous les statuts",
    "status.open_only": "Ouverts seulement",

    # ------------------------------------------------------------------
    # Issues panel
    # ------------------------------------------------------------------
    "issues.col.severity": "Sév.",
    "issues.col.status": "Statut",
    "issues.col.column": "Colonne",
    "issues.col.row": "Ligne",
    "issues.col.message": "Message",
    "issues.col.suggestion": "Suggestion",
    "issues.filter.severity": "Sévérité :",
    "issues.filter.status": "Statut :",
    "issues.filter.column": "Colonne :",
    "issues.filter.all_cols": "Toutes les colonnes",
    "issues.count": "{n} problème(s)",
    "issues.row_label": "(ligne)",
    "issues.ctx.goto": "Aller à la cellule",
    "issues.ctx.ignore": "Ignorer ce problème",
    "issues.ctx.except": "Ajouter une exception…",

    # ------------------------------------------------------------------
    # Find & Fix drawer
    # ------------------------------------------------------------------
    "findfix.title": "Chercher & Corriger",
    "findfix.search.placeholder": "Valeur à rechercher…",
    "findfix.search.label": "Chercher :",
    "findfix.replace.placeholder": "Remplacer par…",
    "findfix.replace.label": "Remplacer :",
    "findfix.fixtype.label": "Type de correctif :",
    "findfix.fixtype.exact_replace": "Remplacer la correspondance exacte",
    "findfix.fixtype.trim_whitespace": "Supprimer les espaces en début et fin",
    "findfix.fixtype.collapse_spaces": "Réduire les espaces multiples",
    "findfix.fixtype.normalize_unicode": "Normaliser l'Unicode",
    "findfix.fixtype.strip_invisible": "Supprimer les caractères invisibles",
    "findfix.fixtype.replace_nbsp": "Remplacer les espaces insécables (NBSP)",
    "findfix.fixtype.normalize_newlines": "Normaliser les retours à la ligne",
    "findfix.col.label": "Dans la colonne :",
    "findfix.col.all": "Toutes les colonnes",
    "findfix.btn.find": "Chercher",
    "findfix.btn.apply_selected": "Appliquer la sélection",
    "findfix.btn.apply_all": "Appliquer tout",
    "findfix.preview.title": "Aperçu des correspondances",
    "findfix.preview.empty": "Aucune recherche effectuée.",
    "findfix.preview.count": "{n} correspondance(s)",
    "findfix.preview.none": "Aucune correspondance trouvée.",
    "findfix.preview.item": "Ligne {row} | {col} : {old} → {new}",
    "findfix.applied": "Appliqué. Relancez la recherche pour vérifier les problèmes restants.",

    # ------------------------------------------------------------------
    # Load dialog
    # ------------------------------------------------------------------
    "load.title": "Ouvrir un tableur",
    "load.group.file": "Fichier",
    "load.placeholder.no_file": "Aucun fichier sélectionné…",
    "load.btn.browse": "Parcourir…",
    "load.group.options": "Options d'import",
    "load.label.sheet": "Feuille :",
    "load.label.header_row": "Ligne d'en-tête :",
    "load.tooltip.header_row": (
        "Numéro de ligne utilisé comme en-têtes de colonnes "
        "(1 = première ligne, par défaut)"
    ),
    "load.label.encoding": "Encodage :",
    "load.encoding.auto": "(détection auto)",
    "load.label.delimiter": "Délimiteur :",
    "load.delimiter.auto": "(détection auto)",
    "load.group.preview": "Aperçu (premières lignes)",
    "load.preview.error_col": "Erreur",
    "load.dialog.title": "Ouvrir un tableur",
    "load.filter.spreadsheets": (
        "Tableurs (*.csv *.xlsx *.xls *.xlsm *.tsv *.txt);;"
        "Tous les fichiers (*)"
    ),

    # ------------------------------------------------------------------
    # Export dialog
    # ------------------------------------------------------------------
    "export.title": "Exporter",
    "export.group.folder": "Dossier de sortie",
    "export.placeholder.folder": "Sélectionner un dossier…",
    "export.btn.browse": "Parcourir…",
    "export.group.formats": "Formats",
    "export.fmt.xlsx": "Tableur nettoyé (XLSX)",
    "export.fmt.csv": "Tableur nettoyé (CSV — délimiteur : ;)",
    "export.fmt.csv_bom": "  UTF-8 BOM (pour Excel sous Windows)",
    "export.fmt.report": "Rapport de validation (TXT)",
    "export.fmt.issues_csv": "Liste des problèmes (CSV — délimiteur : ;)",
    "export.dialog.folder": "Sélectionner le dossier d'export",
    "export.error_title": "Erreurs d'export",

    # ------------------------------------------------------------------
    # Template library dialog
    # ------------------------------------------------------------------
    "tmpl_lib.title": "Bibliothèque de modèles",
    "tmpl_lib.col.name": "Nom",
    "tmpl_lib.col.scope": "Portée",
    "tmpl_lib.col.type": "Type",
    "tmpl_lib.col.path": "Chemin",
    "tmpl_lib.group.apply": "Appliquer le modèle",
    "tmpl_lib.label.base": "Modèle de base :",
    "tmpl_lib.label.overlay": "Surcouche :",
    "tmpl_lib.btn.apply": "Appliquer && Valider",
    "tmpl_lib.btn.edit": "Modifier…",
    "tmpl_lib.btn.duplicate": "Dupliquer",
    "tmpl_lib.btn.delete": "Supprimer",
    "tmpl_lib.btn.import": "Importer…",
    "tmpl_lib.btn.export": "Exporter…",
    "tmpl_lib.msg.no_template": "Aucun modèle",
    "tmpl_lib.msg.select_base": "Veuillez sélectionner un modèle de base.",
    "tmpl_lib.msg.no_selection": "Aucune sélection",
    "tmpl_lib.msg.select_to_edit": "Veuillez sélectionner un modèle à modifier.",
    "tmpl_lib.msg.readonly_title": "Modèle en lecture seule",
    "tmpl_lib.msg.readonly_body": (
        "Les modèles intégrés ne peuvent pas être modifiés directement."
        "\n\nDupliquer d'abord ?"
    ),
    "tmpl_lib.msg.select_to_dup": "Veuillez sélectionner un modèle à dupliquer.",
    "tmpl_lib.msg.dup_error": "Erreur de duplication",
    "tmpl_lib.msg.file_exists": "Fichier existant",
    "tmpl_lib.msg.overwrite": "{name} existe déjà dans les modèles utilisateur. Remplacer ?",
    "tmpl_lib.msg.import_error": "Erreur d'import",
    "tmpl_lib.msg.cannot_delete": "Impossible de supprimer",
    "tmpl_lib.msg.builtin_nodelete": "Les modèles intégrés ne peuvent pas être supprimés.",
    "tmpl_lib.msg.delete_title": "Supprimer le modèle",
    "tmpl_lib.msg.delete_body": "Supprimer le modèle « {name} » ?\nCela supprimera :\n{path}",
    "tmpl_lib.msg.delete_error": "Erreur de suppression",
    "tmpl_lib.msg.select_to_export": "Veuillez sélectionner un modèle à exporter.",
    "tmpl_lib.dialog.import": "Importer un modèle",
    "tmpl_lib.dialog.export": "Exporter le modèle",
    "tmpl_lib.msg.export_error": "Erreur d'export",
    "tmpl_lib.tooltip.readonly": "Modèle intégré (lecture seule). Dupliquer pour modifier.",
    "tmpl_lib.msg.applied": "Modèle appliqué : {id}{overlay}",
    "tmpl_lib.copy_suffix": " (copie)",

    # ------------------------------------------------------------------
    # Template editor dialog
    # ------------------------------------------------------------------
    "tmpl_edit.title": "Modifier le modèle — {name}",
    "tmpl_edit.pane.left.title": "Colonnes / Groupes",
    "tmpl_edit.pane.left.filter": "Filtrer…",
    "tmpl_edit.pane.mid.placeholder": "Sélectionner une colonne à modifier",
    "tmpl_edit.group.profile": "Profil de colonne",
    "tmpl_edit.label.kind": "Type :",
    "tmpl_edit.label.required": "Obligatoire :",
    "tmpl_edit.label.unique": "Unique :",
    "tmpl_edit.label.multiline": "Multiligne :",
    "tmpl_edit.label.preset": "Préréglage :",
    "tmpl_edit.label.regex": "Expression régulière :",
    "tmpl_edit.label.list_sep": "Séparateur de liste :",
    "tmpl_edit.group.overrides": "Surcharges de règles pour cette colonne",
    "tmpl_edit.overrides.help": (
        "Une surcharge par ligne : "
        "<code>règle_id: enabled=true/false severity=ERREUR</code>"
    ),
    "tmpl_edit.overrides.placeholder": (
        "generic.pseudo_missing: enabled=false\n"
        "generic.soft_typing: severity=ERROR"
    ),
    "tmpl_edit.group.global_rules": "Règles globales du modèle",
    "tmpl_edit.global_rules.help": (
        "Modifiez directement le fichier YAML pour configurer les règles globales. "
        "Les surcharges par colonne se définissent via l'éditeur ci-dessus."
    ),
    "tmpl_edit.active_rules": "Règles actives : {rules}",
    "tmpl_edit.active_rules.none": "(aucune)",
    "tmpl_edit.btn.save": "Enregistrer le modèle",
    "tmpl_edit.msg.load_error": "Erreur de chargement",
    "tmpl_edit.msg.load_body": "Impossible de charger le modèle :\n{exc}",
    "tmpl_edit.msg.save_error": "Erreur d'enregistrement",
    "tmpl_edit.msg.save_body": "Impossible d'enregistrer le modèle :\n{exc}",
    "tmpl_edit.wildcard": "* (toutes les colonnes)",
    "tmpl_edit.group_prefix": "[groupe]",

    # Preset display names
    "preset.none": "(aucun)",
    "preset.w3c_dtf_date": "Date (W3C DTF / AAAA-MM-JJ)",
    "preset.uri": "URI",
    "preset.email": "Courriel",
    "preset.orcid": "ORCID",
    "preset.creator_name": "Nom du créateur",
    "preset.custom_regex": "Regex personnalisée",
    "preset.regex.placeholder": "Motif regex personnalisé (quand préréglage=custom_regex)",

    # ------------------------------------------------------------------
    # Project controller dialogs
    # ------------------------------------------------------------------
    "project.open_dialog": "Ouvrir un dossier de projet",
    "project.not_a_project": "Pas un dossier de projet",
    "project.no_yml": "Aucun fichier project.yml trouvé dans :\n{folder}",
    "project.error_title": "Erreur de projet",
    "project.error_body": "Impossible de lire le projet :\n{exc}",
    "project.missing_file": "Fichier source manquant",
    "project.missing_file_body": "Fichier source introuvable :\n{path}",
    "project.save_dialog": "Enregistrer le projet sous — Choisir le dossier",
    "project.no_file_title": "Aucun fichier chargé",
    "project.no_file_body": "Ouvrez un fichier avant d'enregistrer un projet.",
    "project.save_error": "Erreur d'enregistrement",
    "project.save_error_body": "Impossible d'enregistrer le projet :\n{exc}",

    # ------------------------------------------------------------------
    # Load controller dialogs
    # ------------------------------------------------------------------
    "load.error_title": "Erreur de chargement",
    "load.error_body": "Impossible de charger le fichier :\n{exc}",

    # ------------------------------------------------------------------
    # TXT Report headings (exporters.py)
    # ------------------------------------------------------------------
    "report.header": "TABLERREUR — Rapport de validation",
    "report.generated": "Généré le :",
    "report.source": "Fichier source :",
    "report.shape": "Dimensions :",
    "report.encoding": "Encodage :",
    "report.summary": "RÉSUMÉ",
    "report.top_cols": "COLONNES LES PLUS AFFECTÉES",
    "report.top_types": "TYPES DE PROBLÈMES LES PLUS FRÉQUENTS",
    "report.details": "DÉTAILS (PROBLÈMES OUVERTS)",
    "report.issue_count": "problème(s)",
    "report.suggestion": "→ Suggestion :",
    "report.row": "Ligne",
    "report.total": "TOTAL",

    # ------------------------------------------------------------------
    # Issues CSV column headers (exporters.py)
    # ------------------------------------------------------------------
    "csv.issue_id": "identifiant",
    "csv.severity": "sévérité",
    "csv.status": "statut",
    "csv.rule_id": "règle",
    "csv.row": "ligne",
    "csv.column": "colonne",
    "csv.message": "message",
    "csv.original_value": "valeur_originale",
    "csv.suggestion": "suggestion",
    "csv.detected_at": "détecté_le",

    # ------------------------------------------------------------------
    # XLSX sheet names (exporters.py)
    # ------------------------------------------------------------------
    "xlsx.sheet.data": "Données",
    "xlsx.sheet.issues": "Problèmes",
}

# ---------------------------------------------------------------------------
# Active language (only FR for now)
# ---------------------------------------------------------------------------

_ACTIVE: dict[str, str] = FR


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def t(key: str, **kwargs: object) -> str:
    """Return the UI string for *key*, with optional format substitutions.

    If the key is not found, returns the key itself (fail-visible).

    Examples::

        t("app.title")
        t("status.loaded", name="data.csv", rows=100, cols=5)
    """
    template = _ACTIVE.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template
    return template


def severity_label(value: str) -> str:
    """Return the French display label for a severity enum value string.

    Args:
        value: One of "ERROR", "WARNING", "SUSPICION"

    Returns:
        French label, e.g. "Erreur". Falls back to the value itself.
    """
    return _ACTIVE.get(f"severity.{value}", value)


def status_label(value: str) -> str:
    """Return the French display label for an IssueStatus enum value string.

    Args:
        value: One of "OPEN", "FIXED", "IGNORED", "EXCEPTED"

    Returns:
        French label, e.g. "Ouvert". Falls back to the value itself.
    """
    return _ACTIVE.get(f"status.{value}", value)


def kind_label(value: str) -> str:
    """Return the French display label for a ColumnKind value string."""
    return _ACTIVE.get(f"kind.{value}", value)


def preset_label(value: str) -> str:
    """Return the French display label for a column preset name."""
    return _ACTIVE.get(f"preset.{value}", value)
