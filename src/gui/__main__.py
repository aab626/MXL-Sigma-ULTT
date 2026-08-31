"""Entry point: `uv run python -m gui`.

Supports a hidden ``--smoke`` flag used by the release build: it constructs
the real window offscreen, tears it down and exits 0. Windowed binaries have
no console on Windows, so the exit code is the only observable contract.
"""

import sys
from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from gui.theme import STYLESHEET
from gui.window import MainWindow


def _fonts_dir() -> Path:
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return Path(bundled) / "gui" / "assets" / "fonts"
    return Path(__file__).parent / "assets" / "fonts"


def load_fonts() -> None:
    for ttf in sorted(_fonts_dir().glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))


def main() -> None:
    if "--smoke" in sys.argv[1:]:
        _run_smoke()
        return

    app = QApplication(sys.argv)
    app.setApplicationName("MXL Sigma Lag Test Tool")
    app.setStyleSheet(STYLESHEET)
    load_fonts()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


def _run_smoke() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    load_fonts()
    window = MainWindow()
    window.show()
    app.processEvents()
    window.close()
    print("smoke ok")
    sys.exit(0)


if __name__ == "__main__":
    main()
