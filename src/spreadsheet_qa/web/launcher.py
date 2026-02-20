"""Launcher standalone pour Tablerreur Web.

Lance uvicorn sur un port libre, attend la disponibilité du serveur,
puis ouvre le navigateur par défaut.

Usage :
    python -m spreadsheet_qa.web
"""

from __future__ import annotations

import argparse
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from subprocess import DEVNULL

try:
    import uvicorn
    from spreadsheet_qa.web.app import app as _web_app
    _UVICORN_AVAILABLE = True
except ImportError:
    _UVICORN_AVAILABLE = False


def find_free_port(start: int = 8400, end: int = 8500) -> int:
    """Return the first free TCP port in [start, end)."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"Aucun port libre trouvé entre {start} et {end}.")


def wait_for_health(url: str, timeout: float = 15.0) -> bool:
    """Poll *url* every 200 ms until it returns HTTP 200 or *timeout* elapses."""
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Tablerreur — serveur web")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port TCP à utiliser (si absent, un port libre est choisi automatiquement)",
    )
    args = parser.parse_args()

    # Sidecar mode: port is imposed by Tauri — skip browser open
    sidecar_mode = args.port is not None
    port = args.port if sidecar_mode else find_free_port()

    health_url = f"http://127.0.0.1:{port}/health"
    app_url = f"http://127.0.0.1:{port}"

    print(f"Tablerreur — Démarrage du serveur sur le port {port}…")

    # In a PyInstaller frozen bundle, sys.executable is the frozen binary itself,
    # not a Python interpreter — run uvicorn directly in a thread.
    frozen = getattr(sys, "frozen", False)
    proc = None

    if frozen:
        if not _UVICORN_AVAILABLE:
            print("Erreur : uvicorn non disponible dans le bundle.", file=sys.stderr)
            sys.exit(1)

        def _serve() -> None:
            uvicorn.run(_web_app, host="127.0.0.1", port=port, log_level="warning")

        _thread = threading.Thread(target=_serve, daemon=True)
        _thread.start()
    else:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "spreadsheet_qa.web.app:app",
                "--port",
                str(port),
                "--host",
                "127.0.0.1",
            ],
            stdout=DEVNULL,
            # stderr laissé sur le terminal pour afficher les erreurs de démarrage
        )

    def stop(signum=None, frame=None) -> None:
        print("\nArrêt du serveur Tablerreur…")
        if proc is not None:
            proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    print("En attente de la disponibilité du serveur…")
    ready = wait_for_health(health_url)

    if not ready:
        if proc is not None and proc.poll() is not None:
            print("Erreur : le serveur s'est arrêté de manière inattendue.", file=sys.stderr)
        else:
            print("Erreur : le serveur n'a pas démarré dans les délais.", file=sys.stderr)
            if proc is not None:
                proc.terminate()
        sys.exit(1)

    print(f"Serveur prêt → {app_url}")
    if not sidecar_mode:
        print("Ouverture du navigateur…")
        webbrowser.open(app_url)
        print("Fermez ce terminal (Ctrl+C) pour arrêter Tablerreur.")
    else:
        print("Mode sidecar — navigateur géré par Tauri.")

    if proc is not None:
        proc.wait()
    else:
        # Frozen mode: block until a signal terminates the process
        try:
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            pass
