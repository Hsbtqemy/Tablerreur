#!/usr/bin/env python3
"""Run Tablerreur from the project root without relying on editable install.

Usage (from project root):  python run.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add src/ so that "import spreadsheet_qa" works when not installed
_root = Path(__file__).resolve().parent
_src = _root / "src"
if _src.exists() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from spreadsheet_qa.__main__ import main

if __name__ == "__main__":
    main()
