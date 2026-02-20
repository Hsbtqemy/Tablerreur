# File Format Specifications

## CSV export (output)

| Setting | Value |
|---------|-------|
| Delimiter | `;` (always, non-configurable) |
| Quote char | `"` |
| Quoting | QUOTE_MINIMAL (quote when cell contains `;`, `"`, or newline) |
| Encoding | UTF-8 (default) or UTF-8 with BOM |
| Line ending | OS default via Python `newline=""` mode |

Multi-value in-cell list separator: `|` (not `;`, to avoid ambiguity with CSV delimiter).

## project.yml

```yaml
version: 1
source_file: /path/to/original.csv
template: generic
overlay: nakala                        # optional (legacy field)
active_generic_template: generic_default   # NEW: template ID for base template
active_overlay_template: nakala_baseline   # NEW: overlay template ID (optional)
header_row: 2            # 1-based (row 2 = index 1)
encoding: utf-8
delimiter: ";"
sheet_name: null
fingerprint: <sha256-of-raw-file-bytes[:65536]>
created_at: "2024-02-19T14:30:00+00:00"
```

## work/actions_log.jsonl

One JSON object per line:

```json
{"action_id": "ab12cd34", "timestamp": "2024-02-19T14:35:00+00:00", "action_type": "fix", "scope": "cell", "params": {"row": 5, "col": "Titre", "new_value": "Introduction"}, "stats": {"cells_changed": 1}, "patch_ids": ["ab12cd34_p0"]}
{"action_id": "ef56gh78", "timestamp": "2024-02-19T14:36:00+00:00", "action_type": "undo", "scope": "cell", "params": {"original_action_id": "ab12cd34"}, "patch_ids": ["ab12cd34_p0"]}
```

## work/patches/<patch_id>.json

```json
{
  "patch_id": "ab12cd34_p0",
  "action_id": "ab12cd34",
  "row": 5,
  "col": "Titre",
  "old_value": "Introduction ",
  "new_value": "Introduction",
  "issue_id": "a1b2c3d4e5f6",
  "timestamp": "2024-02-19T14:35:00+00:00"
}
```

Undone patches are moved to `work/patches/undone/`.

## reports/issues_*.csv (`;` delimited)

Columns: `issue_id; severity; status; rule_id; row; column; message; original_value; suggestion; detected_at`

## templates/generic.yml

```yaml
version: 1
name: generic
rules:
  generic.hygiene.leading_trailing_space:
    enabled: true
    severity: WARNING
  # ... other rules ...
column_groups:
  "id_*":
    unique: true
columns:
  "*":
    kind: free_text_short
    required: false
    unique: false
    multiline_ok: false
export:
  csv_delimiter: ";"
  multivalues_mode: in_cell
  list_separator: "|"
```

## work/exceptions.yml

```yaml
cell_exceptions:
  - issue_id: "a1b2c3d4e5f6"
    reason: "Legacy data — known issue"
value_exceptions: []
column_ignores: []
global_ignores: []
```

Precedence: cell_exception > value_exception > column_ignore > global_ignore.

## Template storage locations

| Scope | Location |
|-------|----------|
| Built-in | `src/spreadsheet_qa/resources/templates/builtin/` (shipped with package) |
| User | macOS: `~/Library/Application Support/Tablerreur/templates/` |
| User | Linux: `~/.config/Tablerreur/templates/` |
| User | Windows: `%APPDATA%\Tablerreur\templates\` |
| Project | `<project_folder>/templates/` |

Priority when resolving a template ID: **project > user > builtin**.

## Column rule config schema (in templates)

```yaml
columns:
  "ColumnName":
    kind: free_text_short   # free_text_short | free_text_long | controlled | structured | list
    required: false
    unique: false
    multiline_ok: false
    preset: null            # w3c_dtf_date | uri | email | orcid | creator_name | custom_regex
    regex: null             # custom regex (only when preset=custom_regex)
    list_separator: "|"     # only for kind=list
    pipe_in_cell_warning: false   # warn when | appears in-cell
    rule_overrides:
      generic.pseudo_missing:
        enabled: false       # disable a specific rule for this column
      generic.soft_typing:
        severity: ERROR      # override severity for this column
```
