"""
QApplication configuration and startup.
"""

import asyncio
import logging
import sys
from pathlib import Path

import qasync
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from harness_client.themes import apply_theme
from harness_client.ui.main_window import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def get_system_font() -> QFont:
    """Get a suitable system font."""
    font = QFont()
    font.setPointSize(10)

    # Try fonts in order of preference for Windows
    preferred_fonts = [
        "Microsoft YaHei",
        "Segoe UI",
        "SimHei",
        "Microsoft JhengHei",
        "Arial",
    ]

    available_families = QFontDatabase.families()
    for family in preferred_fonts:
        if family in available_families:
            font.setFamily(family)
            break

    return font


def run():
    """Run the Harness Client application."""
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Harness Client")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("Harness")

    # Set default application font (fixes QFont warnings)
    app.setFont(get_system_font())

    # Apply theme stylesheet (replaces QSS file loading)
    apply_theme(app)

    # Setup async event loop
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run event loop
    with loop:
        loop.run_forever()
