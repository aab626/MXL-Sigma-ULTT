"""Gradient banner for the top of the window.

Background is assets/banner.png (dark, 6.4:1 — the exact banner aspect),
scaled to fill; when the asset is missing a painted dark-red gradient wash
with a soft glow is used as fallback. Left side: title and subtitle with a
clickable forum link. Right side: hell-bovine-wifi.gif, a looping animation
pinned to the far right (sized to fit the fixed banner height).
"""

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QUrl
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontMetrics,
    QImage,
    QImageReader,
    QLinearGradient,
    QMovie,
    QPainter,
    QRadialGradient,
)
from PySide6.QtWidgets import QLabel, QWidget

from gui.theme import ACCENT, BORDER, BRIGHT, FONT_DISPLAY, FONT_MONO, TEXT

_HEIGHT = 90
_MARGIN = 16
_TITLE = "Median XL - Lag Test Tool"
_SUBTITLE = "by star626 · forum thread"
_LINK_TEXT = "forum thread"
_LINK_START = _SUBTITLE.index(_LINK_TEXT)
_FORUM_URL = "https://forum.median-xl.com/viewtopic.php?f=32&t=24270"
_BANNER_IMG = "banner.png"
_GIF_NAME = "hell-bovine-wifi.gif"
_GIF_MAX = QSize(176, 78)
_GIF_CARD_SIDE = 70
_GIF_CARD_RADIUS = 6.0


def _asset_path(name: str) -> Path | None:
    """Locate a bundled asset; None when missing (silent fallback, like fonts)."""
    bundled = getattr(sys, "_MEIPASS", None)
    base = Path(bundled) / "gui" / "assets" if bundled else Path(__file__).parent / "assets"
    path = base / name
    return path if path.is_file() else None


class BannerWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(_HEIGHT)
        self.setMouseTracking(True)
        self._link_rect = QRectF()
        self._gif_label: QLabel | None = None
        self._gif_card_rect = QRectF()
        bg_path = _asset_path(_BANNER_IMG)
        self._bg = QImage(str(bg_path)) if bg_path else QImage()

        path = _asset_path(_GIF_NAME)
        if path is not None:
            intrinsic = QImageReader(str(path)).size()
            if intrinsic.isValid():
                scaled = intrinsic.scaled(
                    _GIF_MAX, Qt.AspectRatioMode.KeepAspectRatio
                )
                movie = QMovie(str(path), parent=self)
                movie.setScaledSize(scaled)
                movie.setCacheMode(QMovie.CacheMode.CacheAll)
                self._gif_label = QLabel(self)
                self._gif_label.setMovie(movie)
                self._gif_label.setFixedSize(scaled)
                movie.start()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        w, h = self.width(), self.height()

        if not self._bg.isNull():
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawImage(QRectF(0, 0, w, h), self._bg)
        else:
            wash = QLinearGradient(0, 0, w, h)
            wash.setColorAt(0.0, QColor("#3a1616"))
            wash.setColorAt(0.55, QColor("#1c0c0c"))
            wash.setColorAt(1.0, QColor("#110606"))
            p.fillRect(0, 0, w, h, wash)

            glow = QRadialGradient(QPointF(w * 0.85, h * 1.15), 170)
            glow.setColorAt(0.0, QColor(232, 60, 60, 40))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(0, 0, w, h, glow)

        if not self._gif_card_rect.isNull():
            r = _GIF_CARD_RADIUS
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 55))
            p.drawRoundedRect(self._gif_card_rect.translated(0, 1.5), r, r)
            p.setBrush(QColor(232, 149, 90, 26))
            p.setPen(QColor(232, 149, 90, 70))
            p.drawRoundedRect(self._gif_card_rect, r, r)
            p.setPen(Qt.PenStyle.NoPen)

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

        p.setPen(QColor(TEXT))
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

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._gif_label is not None:
            gif = self._gif_label
            gif.move(
                self.width() - gif.width() - _MARGIN,
                (_HEIGHT - gif.height()) // 2,
            )
            side = _GIF_CARD_SIDE
            self._gif_card_rect = QRectF(
                gif.x() + (gif.width() - side) / 2,
                gif.y() + (gif.height() - side) / 2,
                side,
                side,
            )
        super().resizeEvent(event)

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
