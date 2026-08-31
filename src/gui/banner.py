"""Gradient banner for the top of the window.

The design's banner (photo + gradient overlay) was reduced to a pure painted
gradient per user choice: dark red diagonal wash, a soft glow lower right, a
glowing accent dot above the centered title and subtitle. No image assets.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

from gui.theme import ACCENT, BORDER, BRIGHT, DIM, FONT_MONO, FONT_SANS

_HEIGHT = 90
_TITLE = "MXL Sigma — Lag Test Tool"
_SUBTITLE = "by Drizak · Unofficial community tool"


class BannerWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(_HEIGHT)
        self._version: str | None = None

    def set_version(self, version: str | None) -> None:
        """Show the app version in the subtitle (None hides it)."""
        self._version = version
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        w, h = self.width(), self.height()

        wash = QLinearGradient(0, 0, w, h)
        wash.setColorAt(0.0, QColor("#3a1616"))
        wash.setColorAt(0.55, QColor("#1c0c0c"))
        wash.setColorAt(1.0, QColor("#110606"))
        p.fillRect(0, 0, w, h, wash)

        glow = QRadialGradient(QPointF(w * 0.85, h * 1.15), 170)
        glow.setColorAt(0.0, QColor(232, 60, 60, 40))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, w, h, glow)

        cx, cy = w / 2, 26
        halo = QRadialGradient(QPointF(cx, cy), 15)
        halo.setColorAt(0.0, QColor(232, 149, 90, 110))
        halo.setColorAt(1.0, QColor(232, 149, 90, 0))
        p.setBrush(halo)
        p.drawEllipse(QPointF(cx, cy), 15, 15)
        p.setBrush(QColor(ACCENT))
        p.drawEllipse(QPointF(cx, cy), 3.5, 3.5)

        title = QFont(FONT_SANS)
        title.setPixelSize(13)
        title.setBold(True)
        title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
        p.setFont(title)
        p.setPen(QColor(BRIGHT))
        p.drawText(QRectF(0, 36, w, 18), Qt.AlignmentFlag.AlignHCenter, _TITLE)

        sub = QFont(FONT_MONO)
        sub.setPixelSize(9)
        sub.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
        p.setFont(sub)
        p.setPen(QColor(DIM))
        subtitle = _SUBTITLE if self._version is None else f"{_SUBTITLE} · v{self._version}"
        p.drawText(QRectF(0, 56, w, 14), Qt.AlignmentFlag.AlignHCenter, subtitle)

        p.setPen(Qt.PenStyle.NoPen)
        p.fillRect(0, h - 1, w, 1, QColor(BORDER))
        p.end()
