#!/usr/bin/env python3
"""check_english_strings.py — Audit des chaînes anglaises dans l'interface utilisateur.

Ce script parcourt les fichiers UI de l'application desktop (src/spreadsheet_qa/ui/)
et signale les chaînes potentiellement anglaises qui ne sont pas passées par t().

Usage::

    python scripts/check_english_strings.py
    python scripts/check_english_strings.py --strict     # sort avec code 1 si des problèmes sont trouvés
    python scripts/check_english_strings.py --path src/  # dossier alternatif
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Termes anglais suspects dans l'interface utilisateur
# ---------------------------------------------------------------------------

# Termes qui NE DOIVENT PAS apparaître comme chaînes littérales dans le code UI.
# Ces termes sont acceptable dans : commentaires, docstrings, identifiants de règles,
# constantes internes (ex. "OPEN", "ERROR" — valeurs d'enum).
ENGLISH_UI_TERMS: list[str] = [
    # Actions / boutons
    "Open file",
    "Open…",
    "Browse…",
    "Save",
    "Export",
    "Import",
    "Apply",
    "Apply all",
    "Cancel",
    "Close",
    "Validate",
    "Find",
    "Replace",
    "Duplicate",
    "Delete",
    "Edit",
    "Settings",
    "Quit",
    # Entités métier
    "Issues",
    "Issue",
    "Fix",
    "Fixes",
    "Find & Fix",
    "Find && Fix",
    "Template",
    "Templates",
    "Report",
    # Étiquettes de colonnes / formulaires
    "Severity:",
    "Status:",
    "Column:",
    "Row:",
    "Message:",
    "Suggestion:",
    "Encoding:",
    "Delimiter:",
    "Header row:",
    "Sheet:",
    "Base template:",
    "Overlay:",
    "Kind:",
    "Required:",
    "Unique:",
    "Allow multiline:",
    "Preset:",
    "Regex:",
    "List separator:",
    "Find:",
    "Replace:",
    "Fix type:",
    "In column:",
    "All columns",
    # Sévérités et statuts affichés
    "All severities",
    "Open only",
    "All statuses",
    # Messages d'état
    "Validating",
    "Loading",
    "Ready",
    "Export complete",
    "Template applied",
    "Project opened",
    "Project saved",
    # Titres de fenêtres / dialogues
    "Open Spreadsheet",
    "Template Library",
    "Edit Template",
    "Export dialog",
    "Load error",
    "Save error",
    "Delete template",
    "No selection",
    "Read-only template",
    "Cannot delete",
    "Duplicate error",
    "File exists",
    "Output folder",
    "Formats",
    "Preview",
    "Matches preview",
    "No search performed",
    "No matches found",
    "Applied",
    # Boutons de l'éditeur de modèles
    "Save Template",
    "Column profile",
    "Columns / Groups",
    "Rule overrides",
    "Template-level rules",
    "Active rules",
    # Rapport TXT
    "Spreadsheet Validation Report",
    "Generated:",
    "Source:",
    "Shape:",
    "SUMMARY",
    "TOP AFFECTED COLUMNS",
    "TOP ISSUE TYPES",
    "DETAILS",
    "Suggestion:",
]

# Patterns regex pour détecter les chaînes littérales suspectes
# On cherche les chaînes entre guillemets (simples ou doubles) dans les fichiers Python
_STR_PATTERN = re.compile(
    r'(?:f?"(?P<dq>[^"\\]*(?:\\.[^"\\]*)*)"'
    r"|f?'(?P<sq>[^'\\]*(?:\\.[^'\\]*)*)')",
    re.MULTILINE,
)

# Lignes à ignorer (commentaires, docstrings, tests, exemples, etc.)
_IGNORE_LINE_PATTERNS = [
    re.compile(r"^\s*#"),              # commentaire Python
    re.compile(r"^\s*\"\"\""),         # début de docstring triple-guillemets
    re.compile(r"^\s*'''"),            # début de docstring triple-apostrophes
    re.compile(r"^\s*logger\."),       # logs techniques
    re.compile(r"^\s*logging\."),
    re.compile(r"^\s*print\("),
    re.compile(r"rule_id\s*="),        # identifiants de règles (gardés en anglais)
    re.compile(r"\.rule_id"),
    re.compile(r"\"generic\.\w"),      # rule ids
    re.compile(r"# noqa"),
    re.compile(r"# i18n-ok"),          # marqueur d'exclusion explicite
    # Type annotations et noms internes (pas affichés à l'utilisateur)
    re.compile(r"IssueStore"),         # nom de classe
    re.compile(r"setObjectName"),      # Qt internal object names
    re.compile(r"ObjectName"),
    re.compile(r"TYPE_CHECKING"),
    re.compile(r"\"IssueStore\""),
    re.compile(r"issue_store:"),       # paramètre de fonction
]

# Fichiers à exclure
_EXCLUDE_DIRS = {"__pycache__", ".git", "tests", "node_modules"}
_EXCLUDE_FILES = {"i18n.py"}  # le fichier i18n lui-même contient des termes anglais intentionnellement


def _should_skip_line(line: str) -> bool:
    return any(pat.search(line) for pat in _IGNORE_LINE_PATTERNS)


def _find_english_strings(path: Path, terms: list[str]) -> list[tuple[int, str, str]]:
    """Return list of (line_number, matched_term, line_content) for suspicious strings."""
    findings: list[tuple[int, str, str]] = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return findings

    for lineno, line in enumerate(content.splitlines(), start=1):
        if _should_skip_line(line):
            continue
        line_lower = line.lower()
        for term in terms:
            if term.lower() in line_lower:
                # Make sure it's inside a string literal (not just a variable name)
                # Quick heuristic: look for the term surrounded by quotes
                if (f'"{term}' in line or f"'{term}" in line
                        or f'{term}"' in line or f"{term}'" in line):
                    findings.append((lineno, term, line.strip()))
                    break  # one finding per line is enough
    return findings


def audit(root: Path, strict: bool = False) -> int:
    """Run the audit and return the number of suspicious findings."""
    ui_dir = root / "src" / "spreadsheet_qa" / "ui"
    if not ui_dir.exists():
        print(f"[ERREUR] Dossier UI introuvable : {ui_dir}", file=sys.stderr)
        return 1

    total_findings = 0
    scanned = 0

    for py_file in sorted(ui_dir.rglob("*.py")):
        if any(part in _EXCLUDE_DIRS for part in py_file.parts):
            continue
        if py_file.name in _EXCLUDE_FILES:
            continue

        findings = _find_english_strings(py_file, ENGLISH_UI_TERMS)
        scanned += 1

        if findings:
            rel = py_file.relative_to(root)
            print(f"\n{rel}:")
            for lineno, term, line in findings:
                print(f"  ligne {lineno:4d} | [{term}]  {line[:100]}")
            total_findings += len(findings)

    print(f"\n{'=' * 60}")
    print(f"Fichiers analysés : {scanned}")
    print(f"Occurrences suspectes : {total_findings}")
    if total_findings == 0:
        print("✅ Aucune chaîne anglaise suspecte détectée.")
    else:
        print(f"⚠️  {total_findings} occurrence(s) potentiellement non traduites.")
        print("   Vérifiez et remplacez par t('clé') depuis spreadsheet_qa.ui.i18n")

    return total_findings if strict else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit des chaînes anglaises dans l'interface utilisateur Tablerreur."
    )
    parser.add_argument(
        "--path", default=".", help="Dossier racine du projet (défaut : répertoire courant)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Quitte avec code 1 si des problèmes sont détectés (utile en CI)",
    )
    args = parser.parse_args()

    root = Path(args.path).resolve()
    print(f"Tablerreur — Vérification des chaînes UI anglaises")
    print(f"Racine du projet : {root}")
    print(f"{'=' * 60}")

    result = audit(root, strict=args.strict)
    sys.exit(result)


if __name__ == "__main__":
    main()
