#!/usr/bin/env python3
"""Package the Tablerreur web launcher as a standalone sidecar (onedir mode).

Usage:
    python scripts/build_sidecar.py

The script:
1. Detects the current platform triple (aarch64-apple-darwin, etc.)
2. Runs PyInstaller to build a one-directory bundle (--onedir, not --onefile)
   PyInstaller's --strip strips .so/.dylib debug symbols (safe).
   The main executable is NOT stripped post-build (would invalidate macOS code signature).
3. Copies the entire directory to src-tauri/binaries/tablerreur-backend-{triple}/
4. Updates src-tauri/tauri.conf.json (resources key instead of externalBin)
5. Smoke-tests the executable and reports the startup time

Why --onedir vs --onefile?
  --onefile extracts itself to a temp dir on every launch → 25-37 s cold start.
  --onedir ships pre-extracted libs → sub-5 s startup (often < 2 s).
"""

from __future__ import annotations

import json
import os
import platform
import shutil
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

# Modules to exclude — GUI toolkits, dev tools, and packages present in the
# build interpreter but irrelevant to a headless web sidecar.
EXCLUDES = [
    # GUI toolkits
    "PySide6", "PyQt5", "PyQt6", "PyQt4",
    "tkinter", "_tkinter",
    # Jupyter / IPython
    "IPython", "ipykernel", "notebook",
    # Scientific / visualisation (not used by FastAPI)
    "matplotlib", "scipy",
    "PIL", "Pillow",
    # Testing frameworks
    "pytest", "_pytest",
    # Build / packaging tools
    "setuptools", "pip", "wheel",
    # Debugging / profiling
    "pdb", "profile", "pstats", "cProfile",
    # Interactive terminal
    "curses",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(cmd: list[str], **kwargs) -> None:
    print(f"\n$ {' '.join(str(c) for c in cmd)}\n")
    subprocess.run(cmd, check=True, **kwargs)


def wait_for_health(port: int, timeout: float = 90.0) -> bool:
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


def dir_size(path: Path) -> str:
    """Return human-readable total size of all files under a directory."""
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    for unit in ("o", "Ko", "Mo", "Go"):
        if total < 1024:
            return f"{total:.1f} {unit}"
        total /= 1024
    return f"{total:.1f} To"


def update_tauri_conf(triple: str) -> None:
    """Remove externalBin, add resources mapping for the onedir bundle.

    The resources key maps the platform-specific directory
    src-tauri/binaries/tablerreur-backend-{triple}/ to the name
    "tablerreur-backend" inside the app's resource directory.
    main.rs then resolves the executable via app.path().resource_dir().
    """
    conf_path = REPO_ROOT / "src-tauri" / "tauri.conf.json"
    with conf_path.open("r", encoding="utf-8") as f:
        conf = json.load(f)
    bundle = conf.setdefault("bundle", {})
    bundle.pop("externalBin", None)
    # Array form: Tauri preserves the relative path inside resource_dir.
    # main.rs resolves: resource_dir/binaries/tablerreur-backend-{triple}/{exe,_internal/}
    bundle["resources"] = [
        f"binaries/tablerreur-backend-{triple}/**/*"
    ]
    with conf_path.open("w", encoding="utf-8") as f:
        json.dump(conf, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  tauri.conf.json → resources: binaries/tablerreur-backend-{triple}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    triple = get_target_triple()
    sidecar_name = f"tablerreur-backend-{triple}"
    dest = BINARIES_DIR / sidecar_name

    print("Tablerreur — Packaging sidecar (onedir)")
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

    cmd = [
        build_python, "-m", "PyInstaller",
        "--onedir",          # pre-extracted directory — no temp-dir extraction on launch
        "--noupx",           # skip UPX compression (avoids decompression overhead)
        "-y",                # overwrite dist/ without prompt
        "--name", "tablerreur-backend",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(SPEC_DIR),
        "--add-data", f"{resources_src}{add_data_sep}spreadsheet_qa/resources",
        "--add-data", f"{static_src}{add_data_sep}spreadsheet_qa/web/static",
    ]
    if platform.system() != "Windows":
        cmd.append("--strip")  # strip ELF/Mach-O debug symbols
    for ex in EXCLUDES:
        cmd += ["--exclude-module", ex]
    for hi in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", hi]
    cmd.append(str(launcher))

    run(cmd, cwd=REPO_ROOT)

    # --- Verify the build output (should be a directory, not a file) ---
    built_dir = DIST_DIR / "tablerreur-backend"
    if not built_dir.is_dir():
        print(f"\nErreur : dossier introuvable à {built_dir}", file=sys.stderr)
        sys.exit(1)

    # NOTE: On ne strip PAS manuellement l'exécutable principal après le build.
    # PyInstaller --strip gère déjà le strip des .so/.dylib bundlés.
    # Un strip post-build sur le binaire Mach-O invaliderait la signature de code
    # macOS, ce qui provoque des processus zombies au lancement.

    # --- Copy the entire onedir bundle to src-tauri/binaries/ ---
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(built_dir, dest)

    # Ensure the main executable bit is set (macOS / Linux)
    if platform.system() != "Windows":
        exe_in_dest = dest / "tablerreur-backend"
        if exe_in_dest.exists():
            exe_in_dest.chmod(exe_in_dest.stat().st_mode | 0o111)

    total_size = dir_size(dest)
    print(f"\n{'='*50}")
    print("Sidecar packagé (onedir) :")
    print(f"  Dossier : {dest}")
    print(f"  Taille  : {total_size}")
    print(f"  Triple  : {triple}")
    print(f"{'='*50}\n")

    # --- Update tauri.conf.json to use resources instead of externalBin ---
    update_tauri_conf(triple)

    # --- Smoke test: launch on a test port and measure startup time ---
    test_port = 8499
    exe_in_dest = dest / (
        "tablerreur-backend.exe" if platform.system() == "Windows"
        else "tablerreur-backend"
    )
    print(f"\nTest de démarrage sur le port {test_port}…")
    t0 = time.monotonic()
    proc = subprocess.Popen(
        [str(exe_in_dest), "--port", str(test_port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    startup_time: float = 0.0
    try:
        ready = wait_for_health(test_port, timeout=90.0)
        startup_time = time.monotonic() - t0
        if ready:
            print(f"  ✓ /health a répondu sur le port {test_port}")
        else:
            print(
                f"  ✗ /health n'a pas répondu dans les délais "
                f"({startup_time:.1f}s écoulées)",
                file=sys.stderr,
            )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    if not ready:
        sys.exit(1)

    print(f"\n{'='*50}")
    print("Résumé :")
    print(f"  Taille totale  : {total_size}")
    print(f"  Démarrage      : {startup_time:.2f}s")
    print(f"{'='*50}")
    print("\nPackaging terminé avec succès.")


if __name__ == "__main__":
    main()
