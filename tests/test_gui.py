"""GUI tests: structure and behavior that work without a real display.

PySide6 renders on the offscreen platform, so these run anywhere; they assert
widget wiring rather than pixels (visual checks are done via screenshots).
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets", reason="PySide6 not installed")

from PySide6.QtWidgets import QApplication, QPushButton, QSlider, QTableWidget  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_window_structure(app):
    from gui.window import _ROWS, MainWindow

    w = MainWindow()
    table = w.findChild(QTableWidget)
    assert table is not None
    assert table.rowCount() == len(_ROWS)
    assert table.columnCount() == 6
    assert table.horizontalHeaderItem(2).text() == "Avg"
    assert table.item(len(_ROWS) - 1, 2).text() == "ERR"


def test_chips(app):
    from gui.window import MainWindow

    w = MainWindow()
    chips = [b for b in w.findChildren(QPushButton) if b.property("chip")]
    labels = [b.text() for b in chips]
    assert labels[0] == "All"
    assert "Africa" in labels
    assert "Unsorted" in labels
    assert len(labels) == 8


def test_chips_exclusive(app):
    from gui.window import MainWindow

    w = MainWindow()
    chips = [b for b in w.findChildren(QPushButton) if b.property("chip")]
    chips[3].click()
    assert chips[3].isChecked()
    assert not chips[0].isChecked()
    chips[0].click()
    assert chips[0].isChecked()
    assert not chips[3].isChecked()


def test_tries_slider(app):
    from gui.window import MainWindow

    w = MainWindow()
    slider = w.findChild(QSlider)
    assert (slider.minimum(), slider.maximum()) == (1, 10)
    slider.setValue(7)
    assert w._tries_value.text() == "7"
