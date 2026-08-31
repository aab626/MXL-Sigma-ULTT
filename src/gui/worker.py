"""Background scan worker.

One ScanWorker runs a whole scan off the UI thread: fetch the server
list, apply the selected region filter, resolve the ping mechanism, then
ping everything through core's parallel pinger. Progress is reported as
Qt signals, which Qt automatically delivers on the UI thread, so the
window can update while the scan runs and never has to touch a lock.

The worker accepts a stop event passthrough (from core's pinger) so a
closing window can cancel a scan instead of waiting for it to finish.
"""

import threading
import urllib.error

from PySide6.QtCore import QThread, Signal

from core.config import ConfigError, get_gs_list_url
from core.gslist import (
    GameServer,
    fetch_gs_list,
    filter_servers,
    parse_gs_list,
    unknown_country_codes,
)
from core.pinger import PingError, ping_servers, resolve_concurrency, resolve_mode

UNSORTED = "unsorted"


class ScanWorker(QThread):
    """Runs one scan and reports progress via signals.

    Signal order: resolved (once the list is fetched and filtered), then
    server_started / server_done pairs per row, then scan_done. On
    failure exactly one of fetch_failed / scan_error is emitted and the
    run ends; the UI re-enables its controls on either.
    """

    resolved = Signal(object, int)  # selected servers, unknown-CC count
    server_started = Signal(int)  # row index
    server_done = Signal(int, object)  # row index, list[float | None]
    scan_done = Signal(object, int)  # ping lists in row order, tries
    fetch_failed = Signal(str)
    scan_error = Signal(str)

    def __init__(self, region: str | None, tries: int, parent=None) -> None:
        super().__init__(parent)
        self._region = region
        self._tries = tries
        self._stop = threading.Event()

    def stop(self) -> None:
        """Ask the scan to abandon servers that have not started yet."""
        self._stop.set()

    def run(self) -> None:
        try:
            url = get_gs_list_url()
        except ConfigError as error:
            self.fetch_failed.emit(str(error))
            return

        try:
            text = fetch_gs_list(url)
        except (urllib.error.URLError, OSError, ValueError) as error:
            self.fetch_failed.emit(f"Could not fetch the server list: {error}")
            return

        servers = parse_gs_list(text)
        if not servers:
            self.fetch_failed.emit("The server list is empty.")
            return

        unknown = unknown_country_codes(servers)
        selected = self._filter(servers, unknown)
        if not selected:
            self.fetch_failed.emit("No servers match that filter.")
            return

        try:
            resolve_mode()
        except PingError as error:
            self.scan_error.emit(str(error))
            return

        self.resolved.emit(selected, len(unknown))

        index_of = {server: index for index, server in enumerate(selected)}
        ping_lists = ping_servers(
            selected,
            self._tries,
            concurrency=resolve_concurrency(),
            stop=self._stop,
            on_server_start=lambda server: self.server_started.emit(
                index_of[server]
            ),
            on_server_done=lambda server, pings: self.server_done.emit(
                index_of[server], pings
            ),
        )
        self.scan_done.emit(ping_lists, self._tries)

    def _filter(
        self, servers: list[GameServer], unknown: set[str]
    ) -> list[GameServer]:
        if self._region is None:
            return list(servers)
        if self._region == UNSORTED:
            return [
                server
                for server in servers
                if not server.country_code or server.country_code in unknown
            ]
        return filter_servers(servers, [self._region])
