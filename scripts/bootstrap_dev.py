#!/usr/bin/env python3
"""Post-clone / machine fraîche : installe les dépendances et le sidecar Tauri.

Usage:
    python scripts/bootstrap_dev.py
    python scripts/bootstrap_dev.py --skip-sidecar   # rapide si le sidecar existe déjà
    python scripts/bootstrap_dev.py --skip-npm
    python scripts/bootstrap_dev.py --skip-pip

Prérequis : Python 3.11+, Node.js (npm), Rust (toolchain pour cargo/tauri).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> None:
    print(f"\n→ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd or REPO_ROOT, env=env, check=True)


def step_pip_install() -> None:
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-e",
            ".[web,dev]",
        ]
    )


def step_npm_install() -> None:
    npm = shutil.which("npm")
    if not npm:
        print(
            "npm est introuvable dans le PATH. Installez Node.js puis relancez ce script.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    run([npm, "install"], cwd=REPO_ROOT)


def step_sidecar() -> None:
    run([sys.executable, str(REPO_ROOT / "scripts" / "build_sidecar.py")])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Configure l'environnement de développement Tablerreur après un clone."
    )
    parser.add_argument(
        "--skip-pip",
        action="store_true",
        help="Ne pas exécuter pip install -e .[web,dev]",
    )
    parser.add_argument(
        "--skip-npm",
        action="store_true",
        help="Ne pas exécuter npm install",
    )
    parser.add_argument(
        "--skip-sidecar",
        action="store_true",
        help="Ne pas packager le sidecar PyInstaller (évite plusieurs minutes de build)",
    )
    args = parser.parse_args()

    if REPO_ROOT.name != "Tablerreur":
        # Allow running from other checkout folder names; only warn.
        pass

    print("Tablerreur — configuration post-clone")
    print(f"  Dépôt : {REPO_ROOT}")

    if not args.skip_pip:
        print("\n[1/3] Dépendances Python (éditable + web + dev)…")
        step_pip_install()
    else:
        print("\n[1/3] pip — ignoré (--skip-pip)")

    if not args.skip_npm:
        print("\n[2/3] Dépendances npm (CLI Tauri)…")
        step_npm_install()
    else:
        print("\n[2/3] npm — ignoré (--skip-npm)")

    if not args.skip_sidecar:
        print("\n[3/3] Sidecar Python pour Tauri (PyInstaller, peut prendre plusieurs minutes)…")
        step_sidecar()
    else:
        print("\n[3/3] Sidecar — ignoré (--skip-sidecar)")
        print(
            "  Lancez plus tard : python scripts/build_sidecar.py\n"
            "  (requis avant cargo build / npm run tauri dev)"
        )

    print("\nTerminé. Exemples :")
    print("  python -m spreadsheet_qa.web")
    print("  npm run tauri dev")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"\nÉchec (code {e.returncode}). Corrigez l’erreur ci-dessus puis relancez.", file=sys.stderr)
        raise SystemExit(e.returncode) from e
