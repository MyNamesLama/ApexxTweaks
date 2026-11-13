"""Capture actual uninspected UI states, without simulated hardware or OS changes.

Run with the project's Python 3.13 environment after installing the application.
"""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from tweaker.ui.controller import Controller, PAGES
from tweaker.ui.window import App


def main():
    destination = Path(__file__).resolve().parents[1] / "docs/screenshots"
    destination.mkdir(parents=True, exist_ok=True)
    qt = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as folder:
        window = App(Controller(root=folder))
        window.show()
        qt.processEvents()
        for size, suffix in [((1260, 870), ""), ((920, 540), "-compact")]:
            window.resize(*size)
            for name in PAGES:
                window.navigate(name, animate=False)
                qt.processEvents()
                window.grab().save(
                    str(
                        destination / (name.lower().replace(" ", "-") + suffix + ".png")
                    )
                )
        window.resize(1260, 870)
        window.set_collapsed(True, persist=False)
        window.navigate("Dashboard", animate=False)
        qt.processEvents()
        window.grab().save(str(destination / "sidebar-collapsed.png"))
        window.shutdown()
        window.close()
    print(
        "Captured actual UI pages with isolated empty app data. No diagnostics or Windows mutations were run."
    )


if __name__ == "__main__":
    main()
