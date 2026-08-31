"""Gradient banner for the top of the window.

The design's banner (photo + gradient overlay) was reduced to a pure painted
gradient per user choice: dark red diagonal wash, a soft glow lower right, and
left-aligned title/subtitle with a clickable forum link. No image assets.
"""

from PySide6.QtCore import QPointF, QRectF, Qt, QUrl
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from gui.theme import ACCENT, BORDER, BRIGHT, DIM, FONT_DISPLAY, FONT_MONO

_HEIGHT = 90
_MARGIN = 16
_TITLE = "Median XL - Lag Test Tool"
_SUBTITLE = "by star626 - forum thread"
_LINK_TEXT = "forum thread"
_LINK_START = _SUBTITLE.index(_LINK_TEXT)
_FORUM_URL = "https://forum.median-xl.com/viewtopic.php?f=32&t=24270"


class BannerWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(_HEIGHT)
        self.setMouseTracking(True)
        self._link_rect = QRectF()

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

        title = QFont(FONT_DISPLAY)
        title.setPixelSize(17)
        title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
        p.setFont(title)
        p.setPen(QColor(BRIGHT))
        p.drawText(
            QRectF(_MARGIN, 26, w - _MARGIN * 2, 26),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            _TITLE,
        )

        sub = QFont(FONT_MONO)
        sub.setPixelSize(9)
        sub.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
        p.setFont(sub)
        metrics = QFontMetrics(sub)
        link_x = _MARGIN + metrics.horizontalAdvance(_SUBTITLE[:_LINK_START])
        self._link_rect = QRectF(
            link_x, 52, metrics.horizontalAdvance(_LINK_TEXT), 14
        )

        p.setPen(QColor(DIM))
        p.drawText(
            QRectF(_MARGIN, 52, w - _MARGIN * 2, 14),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            _SUBTITLE,
        )
        link_font = QFont(sub)
        link_font.setUnderline(True)
        p.setFont(link_font)
        p.setPen(QColor(ACCENT))
        p.drawText(
            self._link_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            _LINK_TEXT,
        )

        p.setPen(Qt.PenStyle.NoPen)
        p.fillRect(0, h - 1, w, 1, QColor(BORDER))
        p.end()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._link_rect.contains(event.position())
        ):
            QDesktopServices.openUrl(QUrl(_FORUM_URL))
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        hovering = self._link_rect.contains(event.position())
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if hovering else Qt.CursorShape.ArrowCursor
        )
        self.setToolTip(_FORUM_URL if hovering else "")
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setToolTip("")
        super().leaveEvent(event)
