"""QApplication factory and theme setup."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from spreadsheet_qa.ui.signals import get_signals


def _apply_platform_fixes() -> None:
    """Apply platform-specific fixes (call before QApplication construction)."""
    import os
    import platform
    if platform.system() == "Darwin":
        os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")


def create_app(argv: list[str] | None = None) -> tuple:
    """Create and configure the QApplication and MainWindow.

    Returns:
        (app, window) tuple.
    """
    if argv is None:
        argv = sys.argv

    _apply_platform_fixes()

    # Must be created before any other Qt objects
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv)

    app.setApplicationName("Tablerreur")
    app.setOrganizationName("Tablerreur")
    app.setApplicationDisplayName("Tablerreur — Spreadsheet QA")

    # Respect the system color scheme
    app.styleHints().setColorScheme(Qt.ColorScheme.Unknown)  # follow system

    # Apply a minimal stylesheet for comfortable spacing
    app.setStyleSheet(_STYLESHEET)

    signals = get_signals()

    # Import here to avoid circular imports at module level
    from spreadsheet_qa.ui.main_window import MainWindow

    window = MainWindow(signals)
    return app, window


_STYLESHEET = """
QMainWindow {
    background-color: palette(window);
}

QToolBar {
    spacing: 4px;
    padding: 4px 6px;
    border-bottom: 1px solid palette(mid);
}

QToolBar QToolButton {
    padding: 4px 8px;
    border-radius: 4px;
}

QToolBar QToolButton:hover {
    background-color: palette(highlight);
    color: palette(highlighted-text);
}

QTableView {
    font-size: 13px;
    gridline-color: palette(mid);
    selection-background-color: palette(highlight);
    selection-color: palette(highlighted-text);
}

QHeaderView::section {
    background-color: palette(button);
    padding: 4px 8px;
    border: none;
    border-right: 1px solid palette(mid);
    border-bottom: 1px solid palette(mid);
    font-weight: 600;
}

QDockWidget::title {
    background: palette(button);
    padding: 4px 8px;
    font-weight: 600;
}

QTreeView {
    font-size: 12px;
    selection-background-color: palette(highlight);
}

QGroupBox {
    font-weight: 600;
    margin-top: 8px;
    padding-top: 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    top: 0px;
}

QStatusBar {
    font-size: 12px;
}
"""
