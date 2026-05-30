"""
QApplication configuration and startup.
"""

import asyncio
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import qasync

from harness_client.ui.main_window import MainWindow


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

    # Setup async event loop
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run event loop
    with loop:
        loop.run_forever()
