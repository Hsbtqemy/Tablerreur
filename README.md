# Tablerreur

**Tablerreur** is a cross-platform desktop application for auditing, validating, correcting, and exporting CSV and XLSX spreadsheets.

Built with Python 3.11+ and PySide6 (Qt).

## Installation

```bash
git clone <repo>
cd Tablerreur
pip install -e ".[dev]"
```

## Usage

```bash
python -m spreadsheet_qa
# or
spreadsheet-qa
# If you get "No module named spreadsheet_qa", run from the project root:
python run.py
```

## Features

- Load CSV/XLSX with automatic encoding and delimiter detection
- Choose any row as the header (not necessarily row 1)
- 7 built-in validation rules: hygiene, pseudo-missing values, duplicates, soft typing, rare values, similar values, unexpected multiline
- Issues panel with severity (ERROR / WARNING / SUSPICION) and status (OPEN / FIXED / IGNORED / EXCEPTED)
- Find & Fix drawer with preview and bulk-apply
- Full undo/redo (500-level Command pattern)
- Export: cleaned XLSX, cleaned CSV (always `;` delimiter), TXT report, issues.csv
- YAML templates (`templates/generic.yml` + optional `templates/overlay_nakala.yml`)
- NAKALA overlay: validates deposit types, licenses, languages, W3C-DTF dates

## Troubleshooting

- **No module named spreadsheet_qa** after `pip install -e ".[dev]"`: run from the project root with `python run.py` (this adds `src/` to the path). Or ensure you activated the same environment where you ran pip (e.g. `conda activate tablerreur` then `pip install -e ".[dev]"` and `python -m spreadsheet_qa` from that env).
- **Segmentation fault on macOS**: PySide6/Qt6 can be unstable with Python 3.13 on some macOS (arm64) setups. Use **Python 3.11 or 3.12** (e.g. `conda create -n tablerreur python=3.12` then `pip install -e ".[dev]"`).

## Running tests

```bash
pytest
```

## Documentation

- [SPEC.md](SPEC.md) — product overview
- [docs/architecture.md](docs/architecture.md) — software architecture
- [docs/formats.md](docs/formats.md) — file format specifications
- [docs/ux.md](docs/ux.md) — UX design
- [docs/nakala.md](docs/nakala.md) — NAKALA overlay

## CSV export standard

Output CSV always uses `;` as delimiter, `"` as quote char, UTF-8 encoding.
Multi-value in-cell separator: `|`.

## License

MIT
