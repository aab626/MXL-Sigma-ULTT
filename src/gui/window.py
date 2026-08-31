"""Main window, Phase A: static preview of the design with fake data.

Everything renders exactly as a finished scan will look (values, ERR row,
partial-loss note, top-5 highlighting) so the theme and layout can be checked
against the Figma design. Real scanning arrives in Phase B; the start button
and region chips are visible but intentionally inert.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.gslist import Region
from gui.banner import BannerWidget
from gui.theme import (
    ACCENT,
    ACCENT_10,
    BAD,
    DIM,
    FONT_MONO,
    GOOD,
    OK,
    TEXT,
    ping_color,
)

DEFAULT_TRIES = 4

_REGION_LABELS = {
    Region.NORTH_AMERICA: "N. America",
    Region.SOUTH_AMERICA: "S. America",
    Region.EUROPE: "Europe",
    Region.ASIA: "Asia",
    Region.OCEANIA: "Oceania",
    Region.AFRICA: "Africa",
}

# name, label, avg, min, max, std, lost, all_failed, top_rank
_FakeRow = tuple[str, str, float, float, float, float, int, bool, int | None]

_ROWS: list[_FakeRow] = [
    ("GS5", "Frankfurt", 24.7, 22.9, 30.1, 2.2, 0, False, 1),
    ("GS28", "Sao Paulo", 59.0, 55.1, 64.8, 3.1, 0, False, 2),
    ("GS2", "Moscow", 61.3, 58.0, 70.9, 4.0, 0, False, 3),
    ("GS7", "Paris", 81.4, 76.2, 92.0, 5.5, 1, False, 4),
    ("GS1", "Los Angeles", 96.5, 88.1, 130.2, 14.1, 0, False, 5),
    ("GS12", "Singapore", 124.8, 110.0, 150.3, 12.9, 0, False, None),
    ("GS18", "Sydney", 371.8, 352.4, 402.1, 18.2, 0, False, None),
    ("GS9", "Nowhere", 0.0, 0.0, 0.0, 0.0, 0, True, None),
]


def _mono(px: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    f = QFont(FONT_MONO)
    f.setPixelSize(px)
    f.setWeight(weight)
    return f


def _item(text: str, color: str, font: QFont, align: Qt.AlignmentFlag) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    it.setForeground(QColor(color))
    it.setFont(font)
    it.setTextAlignment(align | Qt.AlignmentFlag.AlignVCenter)
    return it


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MXL Sigma — Lag Test Tool")

        root = QWidget(objectName="root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(BannerWidget())

        body = QWidget(objectName="body")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)
        lay.addWidget(self._build_controls())
        lay.addWidget(self._build_chips())
        self._top5 = self._build_top5()
        lay.addWidget(self._top5)
        lay.addWidget(self._build_table(), stretch=1)
        lay.addWidget(self._build_footer())
        outer.addWidget(body, stretch=1)

        self.setCentralWidget(root)
        self.setFixedSize(576, 700)

    # -- controls ---------------------------------------------------------

    def _build_controls(self) -> QWidget:
        row = QHBoxLayout()
        row.setSpacing(8)

        label = QLabel("Tries:", objectName="triesLabel")
        row.addWidget(label)

        self._tries_slider = QSlider(Qt.Orientation.Horizontal)
        self._tries_slider.setRange(1, 10)
        self._tries_slider.setValue(DEFAULT_TRIES)
        self._tries_slider.setFixedWidth(140)
        row.addWidget(self._tries_slider)

        self._tries_value = QLabel(str(DEFAULT_TRIES), objectName="triesValue")
        self._tries_value.setFixedWidth(16)
        self._tries_value.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        row.addWidget(self._tries_value)

        row.addStretch(1)

        self._start_btn = QPushButton("START SCAN", objectName="startBtn")
        row.addWidget(self._start_btn)

        self._tries_slider.valueChanged.connect(
            lambda v: self._tries_value.setText(str(v))
        )
        return self._wrap(row)

    # -- chips --------------------------------------------------------------

    def _build_chips(self) -> QWidget:
        row = QHBoxLayout()
        row.setSpacing(5)
        self._chip_group = QButtonGroup(self)
        self._chip_group.setExclusive(True)

        chips = [("All", None), *((lbl, reg) for reg, lbl in _REGION_LABELS.items())]
        chips.append(("Unsorted", None))  # shown when unknown-CC servers exist
        for i, (text, _region) in enumerate(chips):
            btn = QPushButton(text)
            btn.setProperty("chip", True)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            self._chip_group.addButton(btn, i)
            row.addWidget(btn)
        row.addStretch(1)
        return self._wrap(row)

    # -- top 5 ---------------------------------------------------------------

    def _build_top5(self) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 2, 0, 0)
        lay.setSpacing(5)

        heading = QLabel("TOP 5 — BEST SERVERS FOR YOU", objectName="top5Heading")
        font = heading.font()
        font.setPixelSize(9)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.1)
        heading.setFont(font)
        lay.addWidget(heading)

        for r in sorted(
            (r for r in _ROWS if r[8] is not None), key=lambda r: r[8]
        ):
            lay.addLayout(self._top5_row(r))
        return box

    def _top5_row(self, r: _FakeRow) -> QHBoxLayout:
        name, label, avg, _mn, _mx, std, lost, failed, rank = r
        row = QHBoxLayout()
        row.setSpacing(8)

        rank_lbl = QLabel(f"#{rank}", objectName="rankLabel")
        rank_lbl.setFixedWidth(20)
        row.addWidget(rank_lbl)

        text = f"{name} · {label}"
        if lost:
            text += f" ({lost}/{DEFAULT_TRIES} lost)"
        row.addWidget(QLabel(text, objectName="serverLabel"), stretch=1)

        if std > 10:
            row.addWidget(QLabel("unstable", objectName="tagLabel"))

        avg_lbl = QLabel(f"{avg:.1f} ms", objectName="avgLabel")
        avg_lbl.setStyleSheet(f"color: {ping_color(avg)};")
        row.addWidget(avg_lbl)
        return row

    # -- table -----------------------------------------------------------------

    def _build_table(self) -> QTableWidget:
        table = QTableWidget(len(_ROWS), 6)
        table.setHorizontalHeaderLabels(["", "Server", "Avg", "Min", "Max", "StdDev"])
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col, width in ((0, 32), (2, 52), (3, 52), (4, 52), (5, 60)):
            table.setColumnWidth(col, width)
        header.setFixedHeight(26)
        header_align = {
            0: Qt.AlignmentFlag.AlignCenter,
            1: Qt.AlignmentFlag.AlignLeft,
            2: Qt.AlignmentFlag.AlignRight,
            3: Qt.AlignmentFlag.AlignRight,
            4: Qt.AlignmentFlag.AlignRight,
            5: Qt.AlignmentFlag.AlignRight,
        }
        for col, align in header_align.items():
            table.horizontalHeaderItem(col).setTextAlignment(
                align | Qt.AlignmentFlag.AlignVCenter
            )

        right = Qt.AlignmentFlag.AlignRight
        center = Qt.AlignmentFlag.AlignCenter

        for row_i, r in enumerate(_ROWS):
            name, label, avg, mn, mx, std, lost, failed, rank = r
            rank_col = _item(
                f"#{rank}" if rank else "",
                ACCENT,
                _mono(10, QFont.Weight.DemiBold),
                center,
            )
            server_text = f"{name} · {label}"
            if lost:
                server_text += f" ({lost}/{DEFAULT_TRIES} lost)"
            server = _item(server_text, TEXT, _mono(11), Qt.AlignmentFlag.AlignLeft)
            if failed:
                avg_it = _item("ERR", DIM, _mono(11), right)
                mn_it = _item("ERR", DIM, _mono(11), right)
                mx_it = _item("ERR", DIM, _mono(11), right)
                std_it = _item("ERR", DIM, _mono(11), right)
            else:
                avg_it = _item(
                    f"{avg:.1f}", ping_color(avg), _mono(11, QFont.Weight.DemiBold), right
                )
                mn_it = _item(f"{mn:.1f}", DIM, _mono(11), right)
                mx_it = _item(f"{mx:.1f}", DIM, _mono(11), right)
                std_it = _item(
                    f"{std:.1f}", OK if std > 10 else DIM, _mono(11), right
                )
            cells = [rank_col, server, avg_it, mn_it, mx_it, std_it]
            if rank:
                bg = QColor(ACCENT_10)
                for c in cells:
                    c.setBackground(bg)
            for col, cell in enumerate(cells):
                table.setItem(row_i, col, cell)
        self._table = table
        return table

    # -- footer ------------------------------------------------------------------

    def _build_footer(self) -> QWidget:
        row = QHBoxLayout()
        row.setSpacing(8)
        legend = QLabel(
            f'<span style="color:{GOOD};font-weight:700;">■</span> &lt;80ms'
            f'&nbsp;&nbsp;<span style="color:{OK};font-weight:700;">■</span> 80–150ms'
            f'&nbsp;&nbsp;<span style="color:{BAD};font-weight:700;">■</span> &gt;150ms',
            objectName="legend",
        )
        row.addWidget(legend)
        row.addStretch(1)
        right = QLabel(
            f"{len(_ROWS)} servers · {DEFAULT_TRIES} tries/server",
            objectName="footerRight",
        )
        row.addWidget(right)
        return self._wrap(row)

    @staticmethod
    def _wrap(layout: QHBoxLayout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w
