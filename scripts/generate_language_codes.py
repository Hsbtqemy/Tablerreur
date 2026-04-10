"""One-off generator: writes language_codes.py from ISO 639 JSON (network)."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/haliaeetus/iso-639/master/data/iso_639-2.json"
OUT = "src/spreadsheet_qa/core/language_codes.py"


def main() -> None:
    data = json.loads(urllib.request.urlopen(URL, timeout=30).read())
    iso1 = sorted({v["639-1"] for v in data.values() if v.get("639-1")})
    iso2 = sorted(data.keys())
    lines = [
        '"""ISO 639-1 and ISO 639-2 language code sets for validation.',
        "",
        "Embedded from ISO 639-2 alpha-3 registry (see scripts/generate_language_codes.py).",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "ISO639_1_CODES: frozenset[str] = frozenset({",
    ]
    for i in range(0, len(iso1), 14):
        chunk = iso1[i : i + 14]
        lines.append("    " + ", ".join(repr(x) for x in chunk) + ",")
    lines.append("})")
    lines.append("")
    lines.append("ISO639_2_CODES: frozenset[str] = frozenset({")
    for i in range(0, len(iso2), 10):
        chunk = iso2[i : i + 10]
        lines.append("    " + ", ".join(repr(x) for x in chunk) + ",")
    lines.append("})")
    lines.append("")
    Path(OUT).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}: ISO639_1={len(iso1)} ISO639_2={len(iso2)}")


if __name__ == "__main__":
    main()
