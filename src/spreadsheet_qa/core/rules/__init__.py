"""Auto-import all rule modules so their @registry.register decorators fire."""

from spreadsheet_qa.core.rules import (  # noqa: F401
    duplicates,
    hygiene,
    multiline,
    nakala_rules,
    pseudo_missing,
    rare_values,
    similar_values,
    soft_typing,
)
