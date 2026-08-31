"""Main window.

Layout mirrors the Figma design; the data comes from real scans. A
ScanWorker runs off the UI thread and reports progress via signals, so
rows fill in live (pending dashes, pinging dots, values or ERR) and the
Top 5 block appears once a scan completes. Fetch and configuration
errors surface in an inline banner above the table.
"""

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
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

from core.gslist import GameServer, Region
from core.output import ServerResult, collect
from core.pinger import current_mode
from gui.banner import BannerWidget
from gui.theme import (
    ACCENT,
    ACCENT_10,
    BAD,
    BORDER,
    DIM,
    FONT_MONO,
    GOOD,
    OK,
    TEXT,
    ping_color,
)
from gui.worker import UNSORTED, ScanWorker

DEFAULT_TRIES = 4
_TOP_N = 5
_STDDEV_WARN = 10.0

_REGION_LABELS = {
    Region.NORTH_AMERICA: "N. America",
    Region.SOUTH_AMERICA: "S. America",
    Region.EUROPE: "Europe",
    Region.ASIA: "Asia",
    Region.OCEANIA: "Oceania",
    Region.AFRICA: "Africa",
}


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


_PING_CYCLE_MS = 1400
_PING_TICK_MS = 16
_BAR_SEGMENT = 0.35


class _PingBar(QWidget):
    """Slim indeterminate bar in a row's value columns while that GS is pinged.

    All bars share one animation clock (MainWindow._ping_tick); each row is
    staggered so the sweeps don't move in lockstep.
    """

    def __init__(self, stagger: float) -> None:
        super().__init__()
        self._stagger = stagger
        self._phase = 0.0

    def set_phase(self, phase: float) -> None:
        self._phase = phase
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        w, h = self.width(), self.height()
        bar_h = 4.0
        y = (h - bar_h) / 2
        p.setBrush(QColor(BORDER))
        p.drawRoundedRect(QRectF(6, y, w - 12, bar_h), 2, 2)
        seg_w = (w - 12) * _BAR_SEGMENT
        t = (self._phase + self._stagger) % 1.0
        x = 6 + t * (w - 12 + seg_w) - seg_w
        p.setBrush(QColor(ACCENT))
        p.drawRoundedRect(QRectF(x, y, seg_w, bar_h), 2, 2)
        p.end()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Median XL - Lag Test Tool")

        self._worker: ScanWorker | None = None
        self._servers: list[GameServer] = []
        self._results: list[ServerResult | None] = []
        self._tries = DEFAULT_TRIES
        self._top5_rows: QWidget | None = None
        self._ping_bars: dict[int, _PingBar] = {}
        self._ping_phase = 0.0
        self._ping_clock = QTimer(self)
        self._ping_clock.setInterval(_PING_TICK_MS)
        self._ping_clock.timeout.connect(self._tick_ping_bars)

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
        lay.addWidget(self._build_error())
        self._top5, self._top5_lay = self._build_top5()
        self._top5.hide()
        lay.addWidget(self._top5)
        lay.addWidget(self._build_table(), stretch=1)
        lay.addWidget(self._build_footer())
        outer.addWidget(body, stretch=1)

        self.setCentralWidget(root)
        self.setFixedSize(576, 700)

        self._start_btn.clicked.connect(self._start_scan)

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
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(
            QLabel(
                "Number of tries to measure latency to each GS",
                objectName="triesHint",
            )
        )
        lay.addLayout(row)
        return box

    # -- chips --------------------------------------------------------------

    def _build_chips(self) -> QWidget:
        row = QHBoxLayout()
        row.setSpacing(5)
        self._chip_group = QButtonGroup(self)
        self._chip_group.setExclusive(True)

        chips: list[tuple[str, str | None]] = [("All", None)]
        chips += [(label, region.value) for region, label in _REGION_LABELS.items()]
        chips.append(("Unsorted", UNSORTED))  # shown when unknown-CC servers exist
        for i, (text, region) in enumerate(chips):
            btn = QPushButton(text)
            btn.setProperty("chip", True)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setProperty("region", region)
            self._chip_group.addButton(btn, i)
            row.addWidget(btn)
        row.addStretch(1)
        return self._wrap(row)

    # -- error banner ---------------------------------------------------------

    def _build_error(self) -> QLabel:
        self._error = QLabel("", objectName="errorBanner")
        self._error.setWordWrap(True)
        self._error.hide()
        return self._error

    # -- top 5 ---------------------------------------------------------------

    def _build_top5(self) -> tuple[QWidget, QVBoxLayout]:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 2, 0, 0)
        lay.setSpacing(5)

        heading = QLabel("TOP 5 GS [least latency]", objectName="top5Heading")
        font = heading.font()
        font.setPixelSize(9)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.1)
        heading.setFont(font)
        lay.addWidget(heading)
        return box, lay

    def _top5_row(self, result: ServerResult, place: int) -> QHBoxLayout:
        stats = result.stats
        assert stats is not None  # top-5 rows are never skipped
        row = QHBoxLayout()
        row.setSpacing(8)

        rank_lbl = QLabel(f"#{place}", objectName="rankLabel")
        rank_lbl.setFixedWidth(20)
        row.addWidget(rank_lbl)

        text = f"{result.server.name} · {result.server.label}"
        if result.lost:
            text += f" ({result.lost}/{len(result.pings)} lost)"
        row.addWidget(QLabel(text, objectName="serverLabel"), stretch=1)

        if stats.stddev > _STDDEV_WARN:
            row.addWidget(QLabel("unstable", objectName="tagLabel"))

        avg_lbl = QLabel(f"{stats.average:.1f} ms", objectName="avgLabel")
        avg_lbl.setStyleSheet(f"color: {ping_color(stats.average)};")
        row.addWidget(avg_lbl)
        return row

    # -- table -----------------------------------------------------------------

    def _build_table(self) -> QTableWidget:
        table = QTableWidget(0, 6)
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
        self._footer_right = QLabel("Ready.", objectName="footerRight")
        row.addWidget(self._footer_right)
        return self._wrap(row)

    # -- scan flow -------------------------------------------------------------

    def _selected_region(self) -> str | None:
        button = self._chip_group.checkedButton()
        if button is None:
            return None
        return button.property("region")

    def _start_scan(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._tries = self._tries_slider.value()

        self._set_busy(True)
        for row_index in list(self._ping_bars):
            self._dispose_bar(row_index)
        self._ping_clock.stop()
        self._error.hide()
        self._top5.hide()
        self._table.setRowCount(0)
        self._footer_right.setText("Fetching server list…")

        self._worker = ScanWorker(self._selected_region(), self._tries, parent=self)
        self._worker.resolved.connect(self._on_resolved)
        self._worker.server_started.connect(self._on_server_started)
        self._worker.server_done.connect(self._on_server_done)
        self._worker.scan_done.connect(self._on_scan_done)
        self._worker.fetch_failed.connect(self._on_scan_aborted)
        self._worker.scan_error.connect(self._on_scan_aborted)
        self._worker.start()

    def _set_busy(self, busy: bool) -> None:
        self._start_btn.setEnabled(not busy)
        self._start_btn.setText("SCANNING…" if busy else "START SCAN")
        for button in self._chip_group.buttons():
            button.setEnabled(not busy)
        self._tries_slider.setEnabled(not busy)

    def _on_resolved(self, servers: list[GameServer], unknown_count: int) -> None:
        self._servers = list(servers)
        self._results = [None] * len(servers)

        for button in self._chip_group.buttons():
            if button.property("region") == UNSORTED:
                button.setVisible(unknown_count > 0)

        self._table.setRowCount(len(servers))
        for row_index in range(len(servers)):
            self._fill_pending_row(row_index)
        self._footer_right.setText(
            f"{len(servers)} servers · {self._tries} tries/server"
        )

    def _on_server_started(self, index: int) -> None:
        self._fill_pinging_row(index)

    def _on_server_done(self, index: int, pings: list[float | None]) -> None:
        self._clear_ping_row(index)
        result = collect(self._servers[index], pings)
        self._results[index] = result
        self._fill_result_row(index, result, None)

    def _on_scan_done(self, ping_lists: list[list[float | None]], tries: int) -> None:
        for row_index in list(self._ping_bars):
            self._clear_ping_row(row_index)
        results = [
            collect(server, pings)
            for server, pings in zip(self._servers, ping_lists, strict=True)
        ]
        self._results = results

        ranked = sorted(
            (r for r in results if not r.skipped), key=lambda r: r.stats.average
        )
        ranks = {result: place for place, result in enumerate(ranked[:_TOP_N], 1)}

        self._table.setRowCount(len(results))
        for row_index, result in enumerate(results):
            self._fill_result_row(row_index, result, ranks.get(result))

        self._fill_top5(ranked)
        if ranked:
            self._top5.show()
        mode = current_mode()
        mode_note = f" · {mode}" if mode else ""
        self._footer_right.setText(
            f"{len(results)} servers · {tries} tries/server{mode_note}"
        )
        self._set_busy(False)

    def _on_scan_aborted(self, message: str) -> None:
        for row_index in list(self._ping_bars):
            self._clear_ping_row(row_index)
            if self._results[row_index] is None:
                self._fill_pending_row(row_index)
        self._error.setText(message)
        self._error.show()
        self._footer_right.setText("Ready.")
        self._set_busy(False)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.stop()
            worker.wait(20000)
        super().closeEvent(event)

    # -- row rendering -----------------------------------------------------------

    def _fill_pending_row(self, row_index: int) -> None:
        server = self._servers[row_index]
        cells = [
            _item("", TEXT, _mono(10), Qt.AlignmentFlag.AlignCenter),
            _item(f"{server.name} · {server.label}", TEXT, _mono(11), Qt.AlignmentFlag.AlignLeft),
            _item("—", DIM, _mono(11), Qt.AlignmentFlag.AlignRight),
            _item("—", DIM, _mono(11), Qt.AlignmentFlag.AlignRight),
            _item("—", DIM, _mono(11), Qt.AlignmentFlag.AlignRight),
            _item("—", DIM, _mono(11), Qt.AlignmentFlag.AlignRight),
        ]
        for col, cell in enumerate(cells):
            self._table.setItem(row_index, col, cell)

    def _fill_pinging_row(self, row_index: int) -> None:
        for col in (2, 3, 4, 5):
            self._table.takeItem(row_index, col)
        self._table.setSpan(row_index, 2, 1, 4)
        bar = _PingBar(stagger=(row_index * 0.11) % 1.0)
        self._table.setCellWidget(row_index, 2, bar)
        self._ping_bars[row_index] = bar
        if not self._ping_clock.isActive():
            self._ping_clock.start()

    def _dispose_bar(self, row_index: int) -> None:
        bar = self._ping_bars.pop(row_index, None)
        if bar is not None:
            self._table.removeCellWidget(row_index, 2)
            bar.hide()
            bar.setParent(None)
            bar.deleteLater()

    def _clear_ping_row(self, row_index: int) -> None:
        self._dispose_bar(row_index)
        self._table.setSpan(row_index, 2, 1, 1)
        if not self._ping_bars:
            self._ping_clock.stop()

    def _tick_ping_bars(self) -> None:
        self._ping_phase = (self._ping_phase + _PING_TICK_MS / _PING_CYCLE_MS) % 1.0
        for bar in self._ping_bars.values():
            bar.set_phase(self._ping_phase)

    def _fill_result_row(
        self, row_index: int, result: ServerResult, rank: int | None
    ) -> None:
        server = result.server
        rank_col = _item(
            f"#{rank}" if rank else "",
            ACCENT,
            _mono(10, QFont.Weight.DemiBold),
            Qt.AlignmentFlag.AlignCenter,
        )
        server_text = f"{server.name} · {server.label}"
        if result.lost and result.stats is not None:
            server_text += f" ({result.lost}/{len(result.pings)} lost)"
        server_it = _item(server_text, TEXT, _mono(11), Qt.AlignmentFlag.AlignLeft)

        if result.stats is None:
            value_cells = [
                _item("ERR", DIM, _mono(11), Qt.AlignmentFlag.AlignRight)
                for _ in range(4)
            ]
        else:
            stats = result.stats
            value_cells = [
                _item(
                    f"{stats.average:.1f}",
                    ping_color(stats.average),
                    _mono(11, QFont.Weight.DemiBold),
                    Qt.AlignmentFlag.AlignRight,
                ),
                _item(f"{stats.minimum:.1f}", DIM, _mono(11), Qt.AlignmentFlag.AlignRight),
                _item(f"{stats.maximum:.1f}", DIM, _mono(11), Qt.AlignmentFlag.AlignRight),
                _item(
                    f"{stats.stddev:.1f}",
                    OK if stats.stddev > _STDDEV_WARN else DIM,
                    _mono(11),
                    Qt.AlignmentFlag.AlignRight,
                ),
            ]

        cells = [rank_col, server_it, *value_cells]
        if rank:
            bg = QColor(ACCENT_10)
            for cell in cells:
                cell.setBackground(bg)
        for col, cell in enumerate(cells):
            self._table.setItem(row_index, col, cell)

    # -- top 5 filling -----------------------------------------------------------

    def _fill_top5(self, ranked: list[ServerResult]) -> None:
        rows_widget = QWidget()
        lay = QVBoxLayout(rows_widget)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)
        for place, result in enumerate(ranked[:_TOP_N], 1):
            lay.addLayout(self._top5_row(result, place))

        old = self._top5_rows
        if old is not None:
            self._top5_lay.replaceWidget(old, rows_widget)
            old.deleteLater()
        else:
            self._top5_lay.addWidget(rows_widget)
        self._top5_rows = rows_widget

    # -- misc ----------------------------------------------------------------------

    @staticmethod
    def _wrap(layout: QHBoxLayout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w
