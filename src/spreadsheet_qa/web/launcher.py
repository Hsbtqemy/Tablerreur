"""Launcher standalone pour Tablerreur Web.

Lance uvicorn sur un port libre, attend la disponibilité du serveur,
puis ouvre le navigateur par défaut.

Usage :
    python -m spreadsheet_qa.web
"""

from __future__ import annotations

import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from subprocess import DEVNULL


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
    port = find_free_port()
    health_url = f"http://127.0.0.1:{port}/health"
    app_url = f"http://127.0.0.1:{port}"

    print(f"Tablerreur — Démarrage du serveur sur le port {port}…")

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
        proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    print("En attente de la disponibilité du serveur…")
    ready = wait_for_health(health_url)

    if not ready:
        if proc.poll() is not None:
            print("Erreur : le serveur s'est arrêté de manière inattendue.", file=sys.stderr)
        else:
            print("Erreur : le serveur n'a pas démarré dans les délais.", file=sys.stderr)
            proc.terminate()
        sys.exit(1)

    print(f"Serveur prêt → {app_url}")
    print("Ouverture du navigateur…")
    webbrowser.open(app_url)
    print("Fermez ce terminal (Ctrl+C) pour arrêter Tablerreur.")

    proc.wait()
