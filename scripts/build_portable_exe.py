#!/usr/bin/env python3
"""Crée un .exe portable Windows (tout-en-un) après un build Tauri.

À lancer après `npm run tauri build` sur Windows. Assemble l'exe principal
et le sidecar dans un dossier, puis soit :
- un .zip (toujours produit),
- un seul .exe auto-extractible si 7-Zip (et 7zS.sfx) est disponible.

Usage:
    python scripts/build_portable_exe.py

Prérequis : build Tauri déjà effectué (target/release/tablerreur.exe et
src-tauri/binaries/tablerreur-backend-x86_64-pc-windows-msvc/).
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_TAURI = REPO_ROOT / "src-tauri"
TARGET_RELEASE = SRC_TAURI / "target" / "release"
BUNDLE_DIR = TARGET_RELEASE / "bundle"
WINDOWS_TRIPLE = "x86_64-pc-windows-msvc"
MAIN_EXE = "tablerreur.exe"
SIDECAR_DIR_NAME = f"tablerreur-backend-{WINDOWS_TRIPLE}"
# 7-Zip Extra (contient 7zS.sfx) — version stable
SEVEN_ZIP_EXTRA_URL = "https://www.7-zip.org/a/7z2301-extra.7z"


def get_product_name_and_version():
    with (SRC_TAURI / "tauri.conf.json").open(encoding="utf-8") as f:
        conf = json.load(f)
    return conf.get("productName", "Tablerreur"), conf.get("version", "0.1.0")


def find_7z() -> Path | None:
    for name in ("7z", "7z.exe"):
        p = shutil.which(name)
        if p:
            return Path(p)
    for base in [
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "7-Zip",
        Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "7-Zip",
    ]:
        exe = base / "7z.exe"
        if exe.is_file():
            return exe
    return None


def find_7zs_sfx() -> Path | None:
    # Dans le repo (optionnel)
    in_repo = REPO_ROOT / "scripts" / "tools" / "7zS.sfx"
    if in_repo.is_file():
        return in_repo
    # À côté de 7z.exe (certaines installs 7-Zip)
    seven_z = find_7z()
    if seven_z:
        for d in (seven_z.parent, seven_z.parent / "7zExtra"):
            sfx = d / "7zS.sfx"
            if sfx.is_file():
                return sfx
    return None


def download_7zs_sfx() -> Path | None:
    """Télécharge 7z Extra, extrait 7zS.sfx dans scripts/tools/."""
    tools = REPO_ROOT / "scripts" / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    sfx_dest = tools / "7zS.sfx"
    if sfx_dest.is_file():
        return sfx_dest
    seven_z = find_7z()
    if not seven_z:
        return None
    extra_7z = tools / "7z_extra.7z"
    try:
        print("Téléchargement de 7-Zip Extra (7zS.sfx)…")
        urllib.request.urlretrieve(SEVEN_ZIP_EXTRA_URL, extra_7z)
        subprocess.run(
            [str(seven_z), "x", str(extra_7z), "7zS.sfx", f"-o{tools}", "-y"],
            check=True,
            capture_output=True,
        )
    except Exception as e:
        print(f"Impossible de télécharger/extraire 7zS.sfx : {e}", file=sys.stderr)
        if extra_7z.is_file():
            extra_7z.unlink(missing_ok=True)
        return None
    if extra_7z.is_file():
        extra_7z.unlink(missing_ok=True)
    return sfx_dest if sfx_dest.is_file() else None


def main() -> int:
    if platform.system() != "Windows":
        print("Ce script est prévu pour Windows uniquement.", file=sys.stderr)
        return 1

    product_name, version = get_product_name_and_version()
    main_exe_src = TARGET_RELEASE / MAIN_EXE
    sidecar_src = SRC_TAURI / "binaries" / SIDECAR_DIR_NAME

    if not main_exe_src.is_file():
        print(
            f"Exécutable introuvable : {main_exe_src}\n"
            "Exécutez d’abord : npm run tauri build",
            file=sys.stderr,
        )
        return 1
    if not sidecar_src.is_dir():
        print(
            f"Sidecar introuvable : {sidecar_src}\n"
            "Exécutez d’abord : python scripts/build_sidecar.py",
            file=sys.stderr,
        )
        return 1

    staging = REPO_ROOT / "dist" / "portable_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    # Même arborescence que l’app installée : exe à la racine, resources dans binaries/
    shutil.copy2(main_exe_src, staging / MAIN_EXE)
    (staging / "binaries").mkdir()
    shutil.copytree(sidecar_src, staging / "binaries" / SIDECAR_DIR_NAME)

    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    portable_dir = BUNDLE_DIR / "portable"
    portable_dir.mkdir(exist_ok=True)
    base_name = f"{product_name}_{version}_x64_portable"
    zip_path = portable_dir / f"{base_name}.zip"

    # Zip toujours
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", staging)
    print(f"Portable (zip) : {zip_path}")

    # Exe auto-extractible si 7z + 7zS.sfx
    seven_z = find_7z()
    sfx = find_7zs_sfx() or download_7zs_sfx()
    if seven_z and sfx:
        archive_7z = portable_dir / f"{base_name}.7z"
        subprocess.run(
            [str(seven_z), "a", "-t7z", "-mx=5", str(archive_7z), "*"],
            cwd=staging,
            check=True,
            capture_output=True,
        )
        config = (
            ";!@Install@!UTF-8!\n"
            f'Title="{product_name}"\n'
            'BeginPrompt="Extraction en cours..."\n'
            f'RunProgram="{MAIN_EXE}"\n'
            ";!@InstallEnd@!\n"
        )
        config_path = portable_dir / "sfx_config.txt"
        config_path.write_text(config, encoding="utf-8")
        exe_path = portable_dir / f"{base_name}.exe"
        with open(exe_path, "wb") as out:
            out.write(sfx.read_bytes())
            out.write(config.encode("utf-8"))
            out.write(archive_7z.read_bytes())
        archive_7z.unlink()
        config_path.unlink()
        print(f"Portable (exe tout-en-un) : {exe_path}")
    else:
        print(
            "Pour générer un .exe unique, installez 7-Zip et relancez ce script.\n"
            "Vous pouvez aussi distribuer le .zip : l’utilisateur l’extrait puis lance tablerreur.exe.",
        )

    shutil.rmtree(staging)
    return 0


if __name__ == "__main__":
    sys.exit(main())
