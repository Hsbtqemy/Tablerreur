"""Auto-import all rule modules so their @registry.register decorators fire."""

from spreadsheet_qa.core.rules import (  # noqa: F401
    allowed_values,
    case_rule,
    content_type,
    duplicates,
    forbidden_chars,
    hygiene,
    length,
    list_items,
    multiline,
    nakala_rules,
    pseudo_missing,
    rare_values,
    regex_rule,
    required,
    similar_values,
    soft_typing,
)
