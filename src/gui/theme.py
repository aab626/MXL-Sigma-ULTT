"""Theme constants and the application stylesheet.

Colors and typography mirror the Figma design: a dark Diablo-red card with an
orange accent, DM Sans for prose, JetBrains Mono for numbers and controls,
Diablo (fan font) for the banner title.
"""

BG = "#110606"
SURFACE = "#1c0c0c"
PANEL = "#220e0e"
BORDER = "#3d1a1a"
MUTED = "#5c2a2a"
DIM = "#7a3c3c"
TEXT = "#d4b4b4"
BRIGHT = "#f0dada"
ACCENT = "#e8955a"
GOOD = "#4ade80"
OK = "#fbbf24"
BAD = "#f87171"

# Pre-blended accent alphas (accent at 20% / 10% over SURFACE), used for chip
# backgrounds and top-5 row highlighting. Qt stylesheets handle rgba() poorly
# on some platforms, so we blend once here.
ACCENT_20 = "#45271c"
ACCENT_10 = "#301a14"

# Pre-blended error-banner palette (bad tone over BG).
ERROR_BG = "#2a1111"
ERROR_BORDER = "#8a2626"

FONT_SANS = "DM Sans"
FONT_MONO = "JetBrains Mono"
FONT_DISPLAY = "Diablo"


def ping_color(avg_ms: float) -> str:
    """Latency thresholds shared by the table, top-5 and footer legend."""
    if avg_ms < 80:
        return GOOD
    if avg_ms < 150:
        return OK
    return BAD


STYLESHEET = f"""
QWidget#root {{
    background-color: {BG};
}}
QWidget#body {{
    background-color: {BG};
}}
QLabel {{
    color: {TEXT};
    font-family: "{FONT_SANS}";
    font-size: 11px;
    background: transparent;
}}

/* --- controls row --------------------------------------------------- */
QLabel#triesLabel {{
    color: {DIM};
}}
QLabel#triesValue {{
    color: {ACCENT};
    font-family: "{FONT_MONO}";
    font-size: 11px;
    font-weight: 600;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 12px;
    height: 12px;
    margin: -5px 0;
    border-radius: 6px;
    background: {ACCENT};
}}
QSlider::handle:horizontal:hover {{
    background: {BRIGHT};
}}
QSlider::groove:horizontal:disabled {{
    background: {BORDER};
}}
QSlider::sub-page:horizontal:disabled {{
    background: {MUTED};
}}
QSlider::handle:horizontal:disabled {{
    background: {MUTED};
}}
QPushButton#startBtn {{
    background: transparent;
    border: 1px solid {ACCENT};
    border-radius: 4px;
    padding: 7px 18px;
    color: {ACCENT};
    font-family: "{FONT_MONO}";
    font-size: 11px;
    font-weight: 600;
}}
QPushButton#startBtn:hover {{
    background: {ACCENT_20};
}}
QPushButton#startBtn:pressed {{
    background: {PANEL};
}}
QPushButton#startBtn:disabled {{
    border-color: {BORDER};
    color: {MUTED};
}}

/* --- region chips ----------------------------------------------------- */
QPushButton[chip="true"] {{
    background: transparent;
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 8px;
    color: {DIM};
    font-family: "{FONT_MONO}";
    font-size: 9px;
}}
QPushButton[chip="true"]:hover {{
    border-color: {MUTED};
    color: {TEXT};
}}
QPushButton[chip="true"]:checked {{
    border-color: {ACCENT};
    background: {ACCENT_20};
    color: {ACCENT};
}}

/* --- error banner ----------------------------------------------------- */
QLabel#errorBanner {{
    color: {BAD};
    background: {ERROR_BG};
    border: 1px solid {ERROR_BORDER};
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 10px;
}}

/* --- top 5 ------------------------------------------------------------ */
QLabel#top5Heading {{
    color: {ACCENT};
    font-size: 9px;
}}
QLabel#rankLabel {{
    color: {ACCENT};
    font-family: "{FONT_MONO}";
    font-size: 10px;
    font-weight: 600;
}}
QLabel#serverLabel {{
    color: {BRIGHT};
    font-family: "{FONT_MONO}";
    font-size: 11px;
}}
QLabel#avgLabel {{
    font-family: "{FONT_MONO}";
    font-size: 11px;
    font-weight: 600;
}}
QLabel#tagLabel {{
    color: {OK};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 1px 6px;
    font-size: 9px;
}}

/* --- table ------------------------------------------------------------ */
QTableWidget {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    gridline-color: transparent;
    selection-background-color: transparent;
    font-family: "{FONT_MONO}";
    font-size: 11px;
}}
QTableWidget::item {{
    padding: 0px 6px;
}}
QTableWidget::item:hover {{
    background: {PANEL};
}}
QHeaderView::section {{
    background-color: {SURFACE};
    color: {MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 6px;
    font-family: "{FONT_SANS}";
    font-size: 9px;
    font-weight: 600;
}}
QTableCornerButton::section {{
    background-color: {SURFACE};
    border: none;
}}

/* thin scrollbar (design: 4px thumb) */
QTableWidget QScrollBar:vertical {{
    background: transparent;
    width: 4px;
    margin: 0;
}}
QTableWidget QScrollBar::handle:vertical {{
    background: {MUTED};
    border-radius: 2px;
    min-height: 30px;
}}
QTableWidget QScrollBar::add-line:vertical,
QTableWidget QScrollBar::sub-line:vertical {{
    height: 0;
}}
QTableWidget QScrollBar::add-page:vertical,
QTableWidget QScrollBar::sub-page:vertical {{
    background: transparent;
}}

/* --- footer ----------------------------------------------------------- */
QLabel#legend {{
    color: {DIM};
    font-size: 9px;
}}
QLabel#footerRight {{
    color: {DIM};
    font-family: "{FONT_MONO}";
    font-size: 9px;
}}
QLabel#bannerTitle {{
    color: {BRIGHT};
    font-size: 13px;
    font-weight: 700;
}}
QLabel#bannerSubtitle {{
    color: {DIM};
    font-family: "{FONT_MONO}";
    font-size: 9px;
}}
"""
