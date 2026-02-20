# Architecture

## Layer diagram

```
┌─────────────────────────────────────────────────┐
│  UI Layer (PySide6)                             │
│  ui/main_window.py  ui/panels/  ui/dialogs/    │
│  ui/controllers/    ui/table/   ui/signals.py  │
└───────────────────────┬─────────────────────────┘
                        │ imports from
┌───────────────────────▼─────────────────────────┐
│  Core Layer (pure Python, zero Qt)              │
│  core/models.py   core/engine.py               │
│  core/rules/      core/issue_store.py          │
│  core/commands.py core/history.py              │
│  core/patch.py    core/project.py              │
│  core/dataset.py  core/exporters.py            │
│  core/template.py core/nakala_api.py           │
└─────────────────────────────────────────────────┘
```

The core layer has **zero Qt dependency** and can run headless (tests, CLI).

## Data flow

### Load
```
User: Open → LoadDialog → LoadController.load_file()
  → DatasetLoader.load()         (chardet + csv.Sniffer + pandas)
  → SpreadsheetTableModel        (direct ref to DataFrame, no copy)
  → AppSignals.dataset_loaded    → ValidationController.run_full()
```

### Validate
```
ValidationController.run_full()
  → QRunnable worker (QThreadPool)
    → ValidationEngine.validate(df, columns, config)
      → for each rule × column: rule.check() → list[Issue]
  → back on main thread:
    → IssueStore.replace_all(issues)
    → AppSignals.issues_updated → IssuesPanel.refresh()
    → SpreadsheetTableModel.refresh_all() (repaints cell colors)
```

### Fix
```
User: "Apply" in FindFixDrawer
  → FixController.apply_fix(row, col, new_value)
    → ApplyCellFixCommand(df, row, col, old, new, ...)
    → CommandHistory.push(cmd)
      → cmd.execute():
          df.at[row, col] = new_value
          IssueStore.set_status(issue_id, FIXED)
          PatchWriter.write(patch) → work/patches/
          ProjectManager.append_action_log(entry) → actions_log.jsonl
    → SpreadsheetTableModel.refresh_cell(row, col_idx)
    → AppSignals.patch_applied → IssuesPanel refresh
    → ValidationController.run_partial([col])
```

### Undo
```
Ctrl+Z → FixController.undo() → CommandHistory.undo()
  → cmd.undo():
      df.at[row, col] = old_value
      IssueStore.set_status(issue_id, OPEN)
      PatchWriter.delete(patch_id) → moves to patches/undone/
```

### Export
```
User: Export → ExportDialog → ExportController
  → XLSXExporter.export(df, path)         openpyxl
  → CSVExporter.export(df, path, bom=…)   csv.writer(delimiter=";")
  → TXTReporter.export(issues, path)
  → IssuesCSVExporter.export(issues, path) csv.writer(delimiter=";")
```

## Key classes

| Class | File | Role |
|-------|------|------|
| `SpreadsheetTableModel` | ui/table/table_model.py | Qt model wrapping df (no copy) |
| `IssueStore` | core/issue_store.py | In-memory issues, O(1) by (row,col) |
| `ValidationEngine` | core/engine.py | Stateless, runs all rules |
| `CommandHistory` | core/history.py | Undo/redo deque stack (max 500) |
| `ApplyCellFixCommand` | core/commands.py | Atomic cell fix + patch |
| `PatchWriter` | core/patch.py | Writes JSON patch files |
| `ProjectManager` | core/project.py | project.yml + actions_log.jsonl |
| `AppSignals` | ui/signals.py | Global Qt signal bus |

## Threading

- Validation runs in `QRunnable` (Qt thread pool).
- All Qt model mutations happen on the **main thread** via Qt signals with `QueuedConnection`.
- `IssueStore` is not thread-safe — only accessed from the main thread.
