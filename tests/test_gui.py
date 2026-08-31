"""GUI tests: structure and behavior that work without a real display.

PySide6 renders on the offscreen platform, so these run anywhere; they assert
widget wiring rather than pixels (visual checks are done via screenshots).
Worker pipeline tests call run() synchronously with the network and ping
machinery patched out; window flow tests patch ScanWorker.start to run()
inline so signals are delivered without an event loop.
"""

import os
import threading
import time
import urllib.error

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets", reason="PySide6 not installed")

from PySide6.QtWidgets import QApplication, QPushButton, QSlider, QTableWidget  # noqa: E402

from core.gslist import GameServer  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _fake_servers() -> list[GameServer]:
    return [
        GameServer("GS1", "Frankfurt [de]", "de", "192.0.2.1"),
        GameServer("GS2", "Moscow [ru]", "ru", "192.0.2.2"),
        GameServer("GS3", "Seoul [kr]", "kr", "192.0.2.3"),
        GameServer("GS4", "Mystery [xx]", "xx", "192.0.2.4"),
        GameServer("GS5", "Ghost", "", "192.0.2.5"),
    ]


def _patch_worker(monkeypatch):
    import gui.worker as worker

    servers = _fake_servers()
    ping_lists = [[10.0 + i, 11.0 + i, 12.0 + i, 13.0 + i] for i in range(len(servers))]

    monkeypatch.setattr(worker, "get_gs_list_url", lambda: "file:///fake")
    monkeypatch.setattr(worker, "fetch_gs_list", lambda url, timeout=10.0: "fake")
    monkeypatch.setattr(worker, "parse_gs_list", lambda text: list(servers))
    monkeypatch.setattr(worker, "resolve_mode", lambda: "system-ping")

    def fake_ping_servers(selected, tries, *, concurrency=6, stop=None,
                          on_server_start=None, on_server_done=None):
        for i, server in enumerate(selected):
            pings = [10.0 + i, 11.0 + i, 12.0 + i, 13.0 + i]
            if on_server_start is not None:
                on_server_start(server)
            if on_server_done is not None:
                on_server_done(server, pings)
        return [[10.0 + i, 11.0 + i, 12.0 + i, 13.0 + i] for i in range(len(selected))]

    monkeypatch.setattr(worker, "ping_servers", fake_ping_servers)
    return servers, ping_lists


def test_window_structure(app):
    from gui.window import MainWindow

    w = MainWindow()
    table = w.findChild(QTableWidget)
    assert table is not None
    assert table.rowCount() == 0  # filled after a scan resolves
    assert table.columnCount() == 6
    assert table.horizontalHeaderItem(2).text() == "Avg"


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


def test_worker_pipeline_signals(app, monkeypatch):
    _patch_worker(monkeypatch)
    from gui.worker import ScanWorker

    events: list[tuple] = []
    worker = ScanWorker(None, 4)
    worker.resolved.connect(lambda s, u: events.append(("resolved", len(s), u)))
    worker.server_started.connect(lambda i: events.append(("start", i)))
    worker.server_done.connect(lambda i, p: events.append(("done", i)))
    worker.scan_done.connect(lambda p, t: events.append(("scan_done", t)))
    worker.fetch_failed.connect(lambda m: events.append(("fetch_failed", m)))
    worker.scan_error.connect(lambda m: events.append(("scan_error", m)))
    worker.run()

    # 5 servers; 1 unknown country code ("xx" — the empty one is unsorted, not unknown)
    assert events[0] == ("resolved", 5, 1)
    kinds = [event[0] for event in events]
    assert kinds.count("start") == 5
    assert kinds.count("done") == 5
    assert kinds[-1] == "scan_done"
    assert events[-1][1] == 4  # tries
    assert "fetch_failed" not in kinds and "scan_error" not in kinds
    order = [event for event in events if event[0] in ("start", "done")]
    for i in range(5):
        assert order.index(("start", i)) < order.index(("done", i))


def test_worker_region_filter(app, monkeypatch):
    _patch_worker(monkeypatch)
    from gui.worker import ScanWorker

    picked: list[list] = []
    worker = ScanWorker("asia", 4)
    worker.resolved.connect(lambda s, u: picked.append(list(s)))
    worker.run()
    assert [server.country_code for server in picked[0]] == ["ru", "kr"]


def test_worker_unsorted_filter(app, monkeypatch):
    _patch_worker(monkeypatch)
    from gui.worker import UNSORTED, ScanWorker

    picked: list[list] = []
    worker = ScanWorker(UNSORTED, 4)
    worker.resolved.connect(lambda s, u: picked.append(list(s)))
    worker.run()
    assert [server.country_code for server in picked[0]] == ["xx", ""]


def test_worker_fetch_failure(app, monkeypatch):
    import gui.worker as worker

    monkeypatch.setattr(worker, "get_gs_list_url", lambda: "file:///fake")

    def failing_fetch(url, timeout=10.0):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(worker, "fetch_gs_list", failing_fetch)
    from gui.worker import ScanWorker

    events: list = []
    worker = ScanWorker(None, 4)
    worker.fetch_failed.connect(events.append)
    worker.resolved.connect(lambda s, u: events.append("resolved"))
    worker.run()
    assert len(events) == 1
    assert "Could not fetch the server list" in events[0]


def test_worker_ping_error(app, monkeypatch):
    import gui.worker as worker

    ping_error = worker.PingError

    def failing_mode():
        raise ping_error("no mechanism")

    monkeypatch.setattr(worker, "get_gs_list_url", lambda: "file:///fake")
    monkeypatch.setattr(worker, "fetch_gs_list", lambda url, timeout=10.0: "fake")
    monkeypatch.setattr(worker, "parse_gs_list", lambda text: _fake_servers())
    monkeypatch.setattr(worker, "resolve_mode", failing_mode)
    from gui.worker import ScanWorker

    events: list[str] = []
    scan_worker = ScanWorker(None, 4)
    scan_worker.scan_error.connect(events.append)
    scan_worker.resolved.connect(lambda s, u: events.append("resolved"))
    scan_worker.run()
    assert events == ["no mechanism"]


def test_window_scan_flow(app, monkeypatch):
    """End-to-end through the window: scan fills rows, top5 reveals."""
    _patch_worker(monkeypatch)
    from gui.window import MainWindow
    from gui.worker import ScanWorker

    monkeypatch.setattr(ScanWorker, "start", lambda self: self.run())

    w = MainWindow()
    w._start_scan()

    table = w.findChild(QTableWidget)
    assert table.rowCount() == 5
    # row 0 got real values: avg of [10, 11, 12, 13]
    assert table.item(0, 2).text() == "11.5"
    assert table.item(3, 2).text() == "14.5"
    assert w._start_btn.isEnabled()  # re-enabled after the scan
    assert not w._top5.isHidden()  # revealed after the scan
    assert "5 servers · 4 tries/server" in w._footer_right.text()


def test_window_close_cancels_scan(app, monkeypatch):
    """closeEvent stops the worker instead of hanging on a running scan."""
    import gui.worker as worker

    entered = threading.Event()

    def parking_ping_servers(selected, tries, *, concurrency=6, stop=None,
                             on_server_start=None, on_server_done=None):
        entered.set()
        while stop is None or not stop.is_set():
            time.sleep(0.01)
        return [[None] * tries for _ in selected]

    monkeypatch.setattr(worker, "get_gs_list_url", lambda: "file:///fake")
    monkeypatch.setattr(worker, "fetch_gs_list", lambda url, timeout=10.0: "fake")
    monkeypatch.setattr(worker, "parse_gs_list", lambda text: _fake_servers())
    monkeypatch.setattr(worker, "resolve_mode", lambda: "system-ping")
    monkeypatch.setattr(worker, "ping_servers", parking_ping_servers)

    from gui.window import MainWindow

    w = MainWindow()
    w._start_scan()
    assert entered.wait(5)
    assert w._worker.isRunning()
    w.close()  # must stop the worker and wait for it, not hang
    assert not w._worker.isRunning()
