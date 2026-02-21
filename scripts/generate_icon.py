#!/usr/bin/env python3
"""Generate Tablerreur app icons.

Steps:
  1. Draw a 1024×1024 source PNG (blue rounded square + white "T")
  2. Call `tauri icon` to produce every platform-specific format
     (PNG sizes, .icns, .ico …) in src-tauri/icons/
  3. Print the resulting tauri.conf.json icon list

Usage:
    python scripts/generate_icon.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Deps
# ---------------------------------------------------------------------------
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
ICONS_DIR = REPO_ROOT / "src-tauri" / "icons"
ICONS_DIR.mkdir(parents=True, exist_ok=True)
SOURCE_PNG = ICONS_DIR / "icon_source.png"

# ---------------------------------------------------------------------------
# Design constants
# ---------------------------------------------------------------------------
SIZE = 1024
CORNER_RADIUS = 185           # ~18 % — matches iOS/macOS icon rounding feel
BG_COLOR = (37, 99, 235)      # #2563eb  (primary blue from the splash screen)
MARGIN = 0                    # full-bleed; macOS will apply its own mask

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_SIZE = 610               # generous "T", leaving ~200 px breathing room


# ---------------------------------------------------------------------------
# Step 1 — draw source PNG
# ---------------------------------------------------------------------------
def make_source_png() -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Blue rounded square (full bleed)
    draw.rounded_rectangle(
        [(0, 0), (SIZE - 1, SIZE - 1)],
        radius=CORNER_RADIUS,
        fill=(*BG_COLOR, 255),
    )

    # White "T" — load bold font
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except OSError:
        # Fallback: any bold TTF on the system
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        font = None
        for c in candidates:
            if Path(c).exists():
                font = ImageFont.truetype(c, FONT_SIZE)
                break
        if font is None:
            print("Aucun TTF bold trouvé, utilisation de la police par défaut.")
            font = ImageFont.load_default()

    letter = "T"
    bbox = draw.textbbox((0, 0), letter, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    # Center the glyph (bbox origin may be non-zero)
    x = (SIZE - text_w) // 2 - bbox[0]
    y = (SIZE - text_h) // 2 - bbox[1]
    # Nudge slightly upward for optical centering
    y -= SIZE // 40

    draw.text((x, y), letter, fill=(255, 255, 255, 255), font=font)

    img.save(SOURCE_PNG, "PNG")
    print(f"  Source PNG : {SOURCE_PNG}  ({SIZE}×{SIZE})")


# ---------------------------------------------------------------------------
# Step 2 — tauri icon (generates every platform format)
# ---------------------------------------------------------------------------
def run_tauri_icon() -> None:
    """Invoke `tauri icon <source>` to produce all icon variants."""
    npm = shutil.which("npm") or "/Users/hsmy/.nvm/versions/node/v20.11.0/bin/npm"
    if not Path(npm).exists():
        print("npm introuvable — génération des icônes Tauri ignorée.")
        return

    cmd = [
        npm, "run", "tauri", "--",
        "icon",
        str(SOURCE_PNG),
        "--output", str(ICONS_DIR),
    ]
    print(f"\n$ {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=False)
    if result.returncode != 0:
        print(f"Avertissement : tauri icon a retourné le code {result.returncode}.",
              file=sys.stderr)


# ---------------------------------------------------------------------------
# Step 3 — list generated files
# ---------------------------------------------------------------------------
def list_icons() -> None:
    print("\nIcones générées dans src-tauri/icons/ :")
    for f in sorted(ICONS_DIR.glob("*")):
        size = f.stat().st_size
        print(f"  {f.name:35s}  {size:>8,} o")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("Tablerreur — Génération des icônes\n")

    print("1. Dessin de l'icône source (1024×1024)…")
    make_source_png()

    print("\n2. Génération de tous les formats via tauri icon…")
    run_tauri_icon()

    print("\n3. Résultat :")
    list_icons()

    print(
        "\nExtrait tauri.conf.json (section bundle.icon) :\n"
        '  "icon": [\n'
        '    "icons/32x32.png",\n'
        '    "icons/128x128.png",\n'
        '    "icons/128x128@2x.png",\n'
        '    "icons/icon.icns",\n'
        '    "icons/icon.ico"\n'
        '  ]'
    )


if __name__ == "__main__":
    main()
