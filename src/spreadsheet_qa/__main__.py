"""Entry point: python -m spreadsheet_qa"""

from __future__ import annotations

import os
import sys


def _apply_platform_fixes() -> None:
    """Set platform-specific env vars BEFORE any Qt import."""
    import platform
    # Reduce Qt log noise (e.g. "Layer-backing is always enabled" on macOS).
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.drawing=false;qt.qpa.*=false")
    if platform.system() == "Darwin":
        # Note: on macOS PySide6 typically only provides cocoa, minimal, offscreen
        # (no "software" plugin). Do not set QT_QPA_PLATFORM here.
        os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")


def _print_diagnostics() -> None:
    """Print startup diagnostics to stderr for debugging."""
    import platform
    try:
        from PySide6 import __version__ as pyside_version
        from PySide6.QtCore import qVersion
        qt_ver = qVersion()
    except Exception:
        pyside_version = "unknown"
        qt_ver = "unknown"

    print(
        f"[Tablerreur] Python {sys.version.split()[0]} | "
        f"PySide6 {pyside_version} | Qt {qt_ver} | "
        f"{platform.system()} {platform.machine()} | "
        f"prefix={sys.prefix}",
        file=sys.stderr,
    )


def _check_python_macos() -> None:
    """Warn on macOS + Python 3.13 where PySide6 often segfaults."""
    import platform
    if platform.system() != "Darwin":
        return
    if os.environ.get("TABLERREUR_SKIP_PY313_WARNING"):
        return
    ver = sys.version_info
    if ver.major == 3 and ver.minor >= 13:
        print(
            "[Tablerreur] Warning: Python 3.13 on macOS is known to cause Qt segfaults.\n"
            "  Use Python 3.11 or 3.12 instead, e.g.:\n"
            "    conda create -n tablerreur python=3.12 && conda activate tablerreur\n"
            "    pip install -e \".[dev]\"\n"
            "  Set TABLERREUR_SKIP_PY313_WARNING=1 to hide this message.",
            file=sys.stderr,
        )


def main() -> None:
    _check_python_macos()
    _apply_platform_fixes()

    try:
        _print_diagnostics()
        from spreadsheet_qa.ui.app import create_app

        app, window = create_app(sys.argv)
        window.show()
        sys.exit(app.exec())
    except Exception:
        import traceback
        tb = traceback.format_exc()
        print(f"[Tablerreur] Fatal startup error:\n{tb}", file=sys.stderr)

        # Try to show a Qt dialog if Qt itself is available
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            _app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "Tablerreur — startup error",
                f"A fatal error occurred during startup:\n\n{tb}",
            )
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
