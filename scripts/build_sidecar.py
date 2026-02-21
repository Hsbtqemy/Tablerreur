#!/usr/bin/env python3
"""Package the Tablerreur web launcher as a standalone sidecar binary.

Usage:
    python scripts/build_sidecar.py

The script:
1. Detects the current platform triple (aarch64-apple-darwin, etc.)
2. Runs PyInstaller to build a one-file executable
3. Renames the result with the Tauri sidecar triple suffix
4. Copies it to src-tauri/binaries/
5. Prints a summary and does a quick smoke-test
"""

from __future__ import annotations

import os
import platform
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo root (two levels up from this file)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
BINARIES_DIR = REPO_ROOT / "src-tauri" / "binaries"
DIST_DIR = REPO_ROOT / "dist"
BUILD_DIR = REPO_ROOT / "build"
SPEC_DIR = REPO_ROOT  # pyinstaller writes .spec here

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def get_target_triple() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin":
        if machine in ("arm64", "aarch64"):
            return "aarch64-apple-darwin"
        return "x86_64-apple-darwin"
    if system == "Linux":
        return "x86_64-unknown-linux-gnu"
    if system == "Windows":
        return "x86_64-pc-windows-msvc"
    raise RuntimeError(f"Plateforme non supportée : {system} / {machine}")


# ---------------------------------------------------------------------------
# Hidden imports — rules (loaded dynamically via RuleRegistry)
# + uvicorn/anyio internals loaded at runtime
# ---------------------------------------------------------------------------
HIDDEN_IMPORTS = [
    # --- core rules (dynamically registered) ---
    "spreadsheet_qa.core.rules.allowed_values",
    "spreadsheet_qa.core.rules.case_rule",
    "spreadsheet_qa.core.rules.content_type",
    "spreadsheet_qa.core.rules.duplicates",
    "spreadsheet_qa.core.rules.forbidden_chars",
    "spreadsheet_qa.core.rules.hygiene",
    "spreadsheet_qa.core.rules.length",
    "spreadsheet_qa.core.rules.list_items",
    "spreadsheet_qa.core.rules.multiline",
    "spreadsheet_qa.core.rules.nakala_rules",
    "spreadsheet_qa.core.rules.pseudo_missing",
    "spreadsheet_qa.core.rules.rare_values",
    "spreadsheet_qa.core.rules.regex_rule",
    "spreadsheet_qa.core.rules.required",
    "spreadsheet_qa.core.rules.similar_values",
    "spreadsheet_qa.core.rules.soft_typing",
    # --- uvicorn (event loop + HTTP protocol selected at runtime) ---
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    # --- anyio asyncio backend (selected at runtime) ---
    "anyio._backends._asyncio",
    # --- h11 (HTTP/1.1 parser used by uvicorn) ---
    "h11",
    "h11._connection",
    "h11._events",
    "h11._readers",
    "h11._writers",
    # --- starlette internals (sometimes missed by static analysis) ---
    "starlette.routing",
    "starlette.staticfiles",
    "starlette.responses",
    "starlette.middleware.cors",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd: list[str], **kwargs) -> None:
    print(f"\n$ {' '.join(str(c) for c in cmd)}\n")
    subprocess.run(cmd, check=True, **kwargs)


def wait_for_health(port: int, timeout: float = 15.0) -> bool:
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.2)
    return False


def human_size(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("o", "Ko", "Mo", "Go"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} To"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    triple = get_target_triple()
    sidecar_name = f"tablerreur-backend-{triple}"
    dest = BINARIES_DIR / sidecar_name

    print(f"Tablerreur — Packaging sidecar")
    print(f"  Plateforme   : {triple}")
    print(f"  Destination  : {dest}")

    # --- Resolve the Python interpreter to use for building.
    #
    # Build from a dedicated virtualenv (BUILD_VENV_PYTHON env var or
    # auto-detected at $REPO_ROOT/.venv-sidecar/bin/python) when available.
    # Using a clean venv prevents PyInstaller from bundling GUI toolkits
    # (PySide6, matplotlib …) that are present in the system Python but are
    # irrelevant to the web sidecar.
    build_python = sys.executable
    venv_candidates = [
        os.environ.get("BUILD_VENV_PYTHON", ""),
        str(REPO_ROOT / ".venv-sidecar" / "bin" / "python"),
        str(REPO_ROOT / ".venv-sidecar" / "Scripts" / "python.exe"),  # Windows
    ]
    for cand in venv_candidates:
        if cand and Path(cand).is_file():
            build_python = cand
            print(f"  Python build : {build_python}")
            break
    else:
        print(f"  Python build : {build_python} (système — envisagez de créer .venv-sidecar)")

    # --- Ensure PyInstaller is available ---
    import importlib.util
    if importlib.util.find_spec("PyInstaller") is None or build_python != sys.executable:
        print("\nInstallation de PyInstaller dans l'interpréteur de build…")
        run([build_python, "-m", "pip", "install", "pyinstaller", "--quiet"])

    # --- Build PyInstaller command ---
    add_data_sep = ";" if platform.system() == "Windows" else ":"
    resources_src = REPO_ROOT / "src" / "spreadsheet_qa" / "resources"
    static_src = REPO_ROOT / "src" / "spreadsheet_qa" / "web" / "static"
    launcher = REPO_ROOT / "src" / "spreadsheet_qa" / "web" / "launcher.py"

    # Modules to exclude — GUI toolkits bundled by accident because they share
    # the same Python interpreter as PySide6/Qt.
    EXCLUDES = [
        "PySide6", "PyQt5", "PyQt6", "PyQt4",
        "tkinter", "_tkinter",
        "IPython", "ipykernel", "notebook",
        "matplotlib", "scipy",
    ]

    cmd = [
        build_python, "-m", "PyInstaller",
        "--onefile",
        "--name", "tablerreur-backend",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(SPEC_DIR),
        "--add-data", f"{resources_src}{add_data_sep}spreadsheet_qa/resources",
        "--add-data", f"{static_src}{add_data_sep}spreadsheet_qa/web/static",
    ]
    for ex in EXCLUDES:
        cmd += ["--exclude-module", ex]
    for hi in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", hi]
    cmd.append(str(launcher))

    run(cmd, cwd=REPO_ROOT)

    # --- Rename and copy to src-tauri/binaries/ ---
    built = DIST_DIR / "tablerreur-backend"
    if platform.system() == "Windows":
        built = built.with_suffix(".exe")
        sidecar_name += ".exe"
        dest = BINARIES_DIR / sidecar_name

    if not built.exists():
        print(f"\nErreur : exécutable introuvable à {built}", file=sys.stderr)
        sys.exit(1)

    BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built, dest)
    if platform.system() != "Windows":
        dest.chmod(dest.stat().st_mode | 0o111)  # ensure executable bit

    size = human_size(dest)
    print(f"\n{'='*50}")
    print(f"Sidecar packagé :")
    print(f"  Fichier : {dest}")
    print(f"  Taille  : {size}")
    print(f"  Triple  : {triple}")
    print(f"{'='*50}\n")

    # --- Smoke test: launch on a test port and check /health ---
    test_port = 8499
    print(f"Test de démarrage sur le port {test_port}…")
    proc = subprocess.Popen(
        [str(dest), "--port", str(test_port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        ready = wait_for_health(test_port, timeout=90.0)
        if ready:
            print(f"  ✓ /health a répondu sur le port {test_port}")
        else:
            print(f"  ✗ /health n'a pas répondu dans les délais", file=sys.stderr)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    if not ready:
        sys.exit(1)

    print("\nPackaging terminé avec succès.")


if __name__ == "__main__":
    main()
