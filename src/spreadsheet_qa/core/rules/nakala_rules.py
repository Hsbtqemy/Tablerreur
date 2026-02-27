"""Règles de validation NAKALA.

Implémente quatre sous-classes de Rule qui valident les champs de métadonnées NAKALA :

- NakalaCreatedFormatRule  — format de date W3C-DTF (AAAA / AAAA-MM / AAAA-MM-JJ)
- NakalaDepositTypeRule    — vocabulaire contrôlé (api.nakala.fr/deposittypes)
- NakalaLicenseRule        — vocabulaire contrôlé (api.nakala.fr/licenses)
- NakalaLanguageRule       — vocabulaire contrôlé (api.nakala.fr/languages)

NakalaClient est injecté via ``config["_nakala_client"]`` afin que ces règles
restent du Python pur facilement testable sans accès réseau.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd

from spreadsheet_qa.core.coar_mapping import coar_uri_to_label, suggest_coar_uri
from spreadsheet_qa.core.models import Issue, Severity
from spreadsheet_qa.core.rule_base import Rule, registry

_log = logging.getLogger(__name__)

# W3C-DTF subset accepté par NAKALA : AAAA, AAAA-MM ou AAAA-MM-JJ
_CREATED_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


# ---------------------------------------------------------------------------
# NakalaCreatedFormatRule
# ---------------------------------------------------------------------------

@registry.register
class NakalaCreatedFormatRule(Rule):
    rule_id = "nakala.created_format"
    name = "Format de date NAKALA (W3C-DTF)"
    default_severity = "ERROR"
    per_column = True

    def check(
        self, df: pd.DataFrame, col: str | None, config: dict[str, Any]
    ) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        severity = Severity(config.get("severity", self.default_severity))
        pattern_str = config.get("regex", None)
        pattern = re.compile(pattern_str) if pattern_str else _CREATED_RE
        special: list[str] = config.get("special_values") or []
        special_lower = [sv.lower() for sv in special]

        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            cell = str(val).strip()
            if special_lower and cell.lower() in special_lower:
                continue  # valeur spéciale acceptée inconditionnellement
            if not pattern.match(cell):
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=cell,
                        message=(
                            f"Format de date non conforme au W3C-DTF pour la valeur « {cell} » "
                            "(attendu : AAAA, AAAA-MM ou AAAA-MM-JJ)."
                        ),
                        suggestion="Utilisez le format W3C-DTF, ex. : 2024 ou 2024-01-15.",
                    )
                )
        return issues


# ---------------------------------------------------------------------------
# NakalaDepositTypeRule
# ---------------------------------------------------------------------------

@registry.register
class NakalaDepositTypeRule(Rule):
    rule_id = "nakala.deposit_type"
    name = "Type de dépôt NAKALA (vocabulaire COAR)"
    default_severity = "ERROR"
    per_column = True

    def check(
        self, df: pd.DataFrame, col: str | None, config: dict[str, Any]
    ) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        client = config.get("_nakala_client")
        if client is None:
            # Pas de client injecté — silencieux (hors ligne / pas de projet)
            return []

        try:
            vocab: list[str] = client.fetch_deposit_types()
        except Exception as exc:
            _log.warning("nakala.deposit_type : impossible de récupérer le vocabulaire : %s", exc)
            return []

        if not vocab:
            # Vocabulaire vide → hors ligne, on ne génère pas de faux positifs
            return []

        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            cell = str(val).strip()
            if cell in vocab:
                continue

            # Tenter de reconnaître la valeur comme un libellé connu
            suggested_uri = suggest_coar_uri(cell)
            if suggested_uri:
                label_fr = coar_uri_to_label(suggested_uri) or suggested_uri
                message = (
                    f"Type « {cell} » reconnu comme « {label_fr} ». "
                    f"Utilisez l'URI COAR : {suggested_uri}"
                )
                suggestion = suggested_uri
            else:
                message = f"Type de dépôt « {cell} » non reconnu dans le vocabulaire COAR."
                suggestion = "Utilisez une URI COAR depuis api.nakala.fr/vocabularies/datatypes."

            issues.append(
                Issue.create(
                    rule_id=self.rule_id,
                    severity=severity,
                    row=int(row_idx),
                    col=col,
                    original=cell,
                    message=message,
                    suggestion=suggestion,
                )
            )
        return issues


# ---------------------------------------------------------------------------
# NakalaLicenseRule
# ---------------------------------------------------------------------------

@registry.register
class NakalaLicenseRule(Rule):
    rule_id = "nakala.license"
    name = "Licence NAKALA (vocabulaire contrôlé)"
    default_severity = "ERROR"
    per_column = True

    def check(
        self, df: pd.DataFrame, col: str | None, config: dict[str, Any]
    ) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        client = config.get("_nakala_client")
        if client is None:
            return []

        try:
            vocab: list[str] = client.fetch_licenses()
        except Exception as exc:
            _log.warning("nakala.license : impossible de récupérer le vocabulaire : %s", exc)
            return []

        if not vocab:
            return []

        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            cell = str(val).strip()
            if cell not in vocab:
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=cell,
                        message=f"Licence « {cell} » non reconnue dans le vocabulaire NAKALA.",
                        suggestion="Utilisez une licence depuis api.nakala.fr/vocabularies/licenses.",
                    )
                )
        return issues


# ---------------------------------------------------------------------------
# NakalaLanguageRule
# ---------------------------------------------------------------------------

@registry.register
class NakalaLanguageRule(Rule):
    rule_id = "nakala.language"
    name = "Langue NAKALA (RFC 5646 / ISO 639-3)"
    default_severity = "WARNING"
    per_column = True

    def check(
        self, df: pd.DataFrame, col: str | None, config: dict[str, Any]
    ) -> list[Issue]:
        if col is None or col not in df.columns:
            return []

        client = config.get("_nakala_client")
        if client is None:
            return []

        try:
            vocab: list[str] = client.fetch_languages()
        except Exception as exc:
            _log.warning("nakala.language : impossible de récupérer le vocabulaire : %s", exc)
            return []

        if not vocab:
            return []

        severity = Severity(config.get("severity", self.default_severity))
        issues: list[Issue] = []
        for row_idx, val in df[col].items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            cell = str(val).strip()
            if cell not in vocab:
                issues.append(
                    Issue.create(
                        rule_id=self.rule_id,
                        severity=severity,
                        row=int(row_idx),
                        col=col,
                        original=cell,
                        message=(
                            f"Langue « {cell} » non reconnue "
                            "(code ISO 639-3 attendu, ex. : fra, eng, deu)."
                        ),
                        suggestion="Utilisez un code depuis api.nakala.fr/vocabularies/languages.",
                    )
                )
        return issues
