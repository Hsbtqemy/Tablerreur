# UX Design — Studio Minimal

## Principles

- **Respect the system**: follow OS light/dark theme, system fonts (SF Pro / Segoe / Noto).
- **Spacious**: comfortable row heights (28 px), generous padding (8–12 px).
- **Subtle feedback**: cell highlights use muted tones, not loud red/yellow.
- **Suggest, don't force**: never auto-fix. Every fix requires explicit user confirmation.
- **Undo everything**: 500-level undo/redo for all data modifications.

## Keyboard shortcuts

| Action | macOS | Windows / Linux |
|--------|-------|-----------------|
| Open file | ⌘O | Ctrl+O |
| Export | ⌘E | Ctrl+E |
| Validate | ⌘⇧V | Ctrl+Shift+V |
| Find & Fix | ⌘F | Ctrl+F |
| Undo | ⌘Z | Ctrl+Z |
| Redo | ⌘⇧Z | Ctrl+Y |
| Toggle Issues panel | ⌘I | Ctrl+I |
| Quit | ⌘Q | Alt+F4 |

## Cell severity colors

| Severity | Background |
|----------|------------|
| ERROR | Soft red `rgb(255, 220, 220)` |
| WARNING | Soft amber `rgb(255, 243, 200)` |
| SUSPICION | Soft lavender `rgb(230, 230, 255)` |

## Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Toolbar: [Open] [Validate] [Find&Fix] [Undo] [Redo]         │
│           [Templates…] [Export…] [Issues panel]              │
├──────────────────────────────────────┬───────────────────────┤
│                                      │ Issues panel (dock)   │
│  Spreadsheet table view              │ ┌─────────────────┐   │
│  (virtualized, up to 50k rows)       │ │ Sev  Col  Row   │   │
│                                      │ │ WARN Titre  3   │   │
│  Cells coloured by worst severity    │ │ ERR  Date   7   │   │
│                                      │ └─────────────────┘   │
│                                      │ [Go to] [Fix] [Ignore]│
├──────────────────────────────────────┴───────────────────────┤
│  Find & Fix drawer (collapsible, bottom)                      │
│  Find: [_______________]  Replace: [_______________]          │
│  Fix type: [Trim whitespace ▼]   In column: [All ▼]          │
│  [Find] [Apply selected] [Apply all]   3 match(es)           │
└──────────────────────────────────────────────────────────────┘
│ Status bar: Loaded: myfile.csv  (523 rows × 12 cols)  …      │
└──────────────────────────────────────────────────────────────┘
```

## Find & Fix fix types

1. **Replace exact match** — simple string replace (search + replace fields active)
2. **Trim whitespace** — strip leading/trailing spaces from all cells
3. **Collapse spaces** — replace multiple consecutive spaces with one
4. **Normalize unicode** — replace curly quotes, em-dashes, NBSP with ASCII equivalents
5. **Strip invisible chars** — remove zero-width and invisible Unicode code points

## Template Library flow

Open via **Templates…** toolbar button or **Tools → Templates…** menu.

```
┌─ Template Library ──────────────────────────────────────────┐
│  Name              Scope    Type     Path                    │
│  ─────────────────────────────────────────────────────────  │
│  Generic Default   builtin  generic  .../builtin/...         │
│  Generic Strict    builtin  generic  .../builtin/...         │
│  NAKALA Baseline   builtin  overlay  .../builtin/...         │
│  NAKALA Extended   builtin  overlay  .../builtin/...         │
│                                                              │
│  [Apply template]                                            │
│  Base template: [Generic Default ▼]                          │
│  ☐ Overlay:     [NAKALA Baseline ▼]                          │
│  [Apply && Validate]                                         │
│                                                              │
│  [Edit…] [Duplicate] [Delete]   [Import…] [Export…]         │
│                                         [Close]              │
└──────────────────────────────────────────────────────────────┘
```

- Built-in templates are **read-only**. Click "Duplicate" to create a user-editable copy.
- User templates are stored in the per-user config directory (see `docs/formats.md`).
- Project templates live in `<project_folder>/templates/` and take highest priority.

## Template Editor flow

Opened via double-click or "Edit…" in the Template Library.

```
┌─ Edit Template — Generic Default (user copy) ──────────────┐
│  Columns / Groups         Column profile                     │
│  ─────────────────────   ────────────────────────────────   │
│  * (all columns)    ◀    Kind: [free_text_short    ▼]       │
│  [group] id_*            Required: ☐                         │
│  [group] date_*          Unique:   ☐                         │
│  Title                   Allow multiline: ☐                  │
│  Author                  Preset: [(none)            ▼]       │
│                          Regex: [                   ]        │
│                          List separator: [|]                  │
│                                                              │
│                          Rule overrides:                     │
│                          [generic.pseudo_missing: enabled=false]
│                                                              │
│  [Save Template]                        [Cancel]             │
└──────────────────────────────────────────────────────────────┘
```

- Selecting a column or column group populates the middle pane.
- Rule overrides syntax: `<rule_id>: enabled=true/false severity=ERROR`
- Saving writes the YAML file immediately.
