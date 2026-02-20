# NAKALA Overlay

## Overview

The NAKALA overlay adds field-specific validation rules for datasets intended for
deposit in the [NAKALA](https://nakala.fr) research data repository.

Enable it via: **Templates… → Apply template → Overlay → NAKALA Baseline or Extended**.

## Required NAKALA fields

| Field | Kind | Rule |
|-------|------|------|
| `nakala:type` | controlled | Must match COAR deposit types from API |
| `nakala:title` | free_text_short | Required, non-empty |
| `nakala:creator` | structured | Format: `Lastname, Firstname` |
| `nakala:created` | structured | W3C-DTF: `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` |
| `nakala:license` | controlled | Must match NAKALA license vocabulary |

## Recommended fields

| Field | Kind | Notes |
|-------|------|-------|
| `dcterms:description` | free_text_long | Multiline OK; `\|` allowed in text |
| `dcterms:subject` | list | Prefer repeated columns `keywords_*_1..n` |
| `dcterms:language` | controlled | RFC5646 code from API |

## API vocabulary sources

Vocabularies are fetched once and cached to `nakala_cache.json`:

| Vocab | Endpoint |
|-------|---------|
| Deposit types | `https://api.nakala.fr/vocabularies/deposittypes` |
| Licenses | `https://api.nakala.fr/vocabularies/licenses` |
| Languages | `https://api.nakala.fr/vocabularies/languages?limit=10000` |

## Separator policy

- `|` is the multi-value in-cell separator for the tool.
- For NAKALA `description` fields: `|` is allowed as text content (not interpreted as list separator).
- For repeatable fields (`nakala:creator`, `dcterms:subject`): using `|` in-cell triggers a **WARNING** with a suggestion to split to repeated columns.
- Export in NAKALA mode defaults to `multivalues_mode: expanded` (columns `creator_1`, `creator_2`, …).

## Baseline vs Extended comparison

| Feature | NAKALA Baseline | NAKALA Extended |
|---------|----------------|-----------------|
| Required columns (5) | ✅ | ✅ |
| `nakala.deposit_type` rule | ✅ | ✅ |
| `nakala.license` rule | ✅ | ✅ |
| `nakala.created_format` rule | ✅ | ✅ |
| `nakala.language` rule | — | ✅ |
| Recommended fields (`dcterms:*`) | — | ✅ |
| Multilingual column groups (`title_*`) | — | ✅ |
| Keyword columns (`keywords_*`) | — | ✅ |
| Creator format structured check | — | ✅ |
| Identifier/relation URI columns | — | ✅ |

## rule_overrides example

In a template YAML you can override a specific rule for a specific column:

```yaml
columns:
  "nakala:title":
    kind: free_text_short
    required: true
    rule_overrides:
      generic.pseudo_missing:
        enabled: true
        severity: ERROR    # escalate from WARNING to ERROR for this column
      generic.soft_typing:
        enabled: false     # disable soft typing for this column entirely
```

The `rule_overrides` block is per-column and per-rule. It does NOT affect
other columns. The engine applies: `base_rule_config < col_meta < rule_override`.

## Column mapping wizard

The Template Library (Templates… toolbar button) lets you:
1. Select a base template (Generic Default or Generic Strict).
2. Select an overlay (NAKALA Baseline or NAKALA Extended).
3. Apply & Validate — immediately runs validation with the new config.

Column-to-field mapping is handled in the Template Editor (Edit… button):
- Select the column in the left pane.
- Set `kind: controlled` and optionally `preset` for structured formats.
- Rule overrides can disable/escalate specific rules per column.

Vocabulary fetching from the NAKALA API is handled transparently:
- Vocabularies are fetched once and cached to `nakala_cache.json`.
- If offline: vocabulary-based rules (`nakala.deposit_type`, `nakala.license`,
  `nakala.language`) skip silently (no false positives).
- `nakala.created_format` is purely regex-based and works offline.
