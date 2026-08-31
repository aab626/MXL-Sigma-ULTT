"""Entry point: `uv run python -m gui`."""

import sys
from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from gui.theme import STYLESHEET
from gui.window import MainWindow


def load_fonts() -> None:
    fonts_dir = Path(__file__).parent / "assets" / "fonts"
    for ttf in sorted(fonts_dir.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(ttf))


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("MXL Sigma Lag Test Tool")
    app.setStyleSheet(STYLESHEET)
    load_fonts()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
