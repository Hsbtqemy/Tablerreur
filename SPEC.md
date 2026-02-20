# Tablerreur — Spreadsheet QA Tool

**Tablerreur** is a cross-platform desktop application (macOS / Windows / Linux) for auditing, validating, correcting, and exporting CSV and XLSX spreadsheets.

## Quick Start

```bash
pip install -e ".[dev]"
python -m spreadsheet_qa
```

Or with the script entry point:

```bash
spreadsheet-qa
```

## Features

| Feature | Status |
|---------|--------|
| Load CSV / XLSX (any delimiter, any encoding) | ✅ |
| Header row selection (not necessarily row 1) | ✅ |
| 7 built-in validation rules (hygiene, duplicates, …) | ✅ |
| Issues panel with severity / status / column filters | ✅ |
| Find & Fix drawer with preview and bulk apply | ✅ |
| Undo / Redo (Command pattern, 500-level stack) | ✅ |
| Export: XLSX + CSV (`;`) + TXT report + issues.csv | ✅ |
| Project folder mode (project.yml, patches, logs) | ✅ |
| YAML templates (generic + NAKALA overlay) | ✅ |
| NAKALA overlay (COAR, licenses, RFC5646 languages) | ✅ |

## Validation Rules

| Rule ID | Severity | Description |
|---------|----------|-------------|
| `generic.hygiene.leading_trailing_space` | WARNING | Leading or trailing whitespace |
| `generic.hygiene.multiple_spaces` | WARNING | Multiple consecutive spaces |
| `generic.hygiene.unicode_chars` | SUSPICION | Curly quotes, em-dashes, NBSP |
| `generic.hygiene.invisible_chars` | WARNING | Zero-width and invisible chars |
| `generic.pseudo_missing` | WARNING | NA, N/A, NULL, -, ? tokens |
| `generic.duplicate_rows` | WARNING | Fully duplicate rows |
| `generic.unique_column` | ERROR | Duplicates in unique-marked column |
| `generic.soft_typing` | SUSPICION | Type outliers (≥95% typed column) |
| `generic.rare_values` | SUSPICION | Hapax values in categorical columns |
| `generic.similar_values` | SUSPICION | Near-duplicate strings (rapidfuzz) |
| `generic.unexpected_multiline` | WARNING | Newlines in non-multiline columns |

## CSV Export Standard

- Delimiter: **always `;`**
- Quote char: `"`
- Quoting: QUOTE_MINIMAL (cells containing `;`, `"`, or newlines are quoted)
- Encoding: UTF-8 (or UTF-8 with BOM for Excel on Windows)

## Architecture

See [docs/architecture.md](docs/architecture.md).

## NAKALA Overlay

See [docs/nakala.md](docs/nakala.md).
