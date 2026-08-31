"""ICMP pinging with a privilege fallback chain.

Resolution order (detected once per process, via a loopback probe):
1. Unprivileged ICMP (icmplib)     - works on Windows, macOS and Linux with
                                     net.ipv4.ping_group_range configured
2. Privileged ICMP (icmplib)       - works as root
3. System ``ping`` binary          - works almost everywhere (setuid/setcap)

Failed attempts are reported as ``None`` so callers keep the old tool's
skip semantics: failures never enter min/max/avg/stddev.
"""

import os
import platform
import re
import subprocess
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor

import icmplib
from icmplib.exceptions import ICMPLibError, SocketPermissionError

from core.gslist import GameServer

MODE_ICMP_UNPRIVILEGED = "icmp-unprivileged"
MODE_ICMP_PRIVILEGED = "icmp-privileged"
MODE_SYSTEM_PING = "system-ping"

DEFAULT_TIMEOUT = 2.0
DEFAULT_PAYLOAD_SIZE = 32
DEFAULT_CONCURRENCY = 6

CONCURRENCY_ENV = "MXL_PING_CONCURRENCY"
MAX_CONCURRENCY = 16

_LOOPBACK = "127.0.0.1"
_PROBE_TIMEOUT = 1.0
# Same size as real pings: some iputils builds suppress the "time=" field
# for tiny payloads, and the probe must see normal output.
_PROBE_PAYLOAD_SIZE = DEFAULT_PAYLOAD_SIZE

_TIME_PATTERN = re.compile(r"time[=<]\s*([\d.,]+)\s*ms", re.IGNORECASE)
# Linux "rtt min/avg/max/mdev = a/b/c/d ms" and macOS
# "round-trip min/avg/max/stddev = a/b/c/d ms"; some iputils builds
# omit the per-reply "time=" field entirely.
_RTT_SUMMARY_PATTERN = re.compile(r"=\s*[\d.,]+/([\d.,]+)/[\d.,]+/[\d.,]+\s*ms")
_LOOSE_PATTERN = re.compile(r"[=<]\s*(\d+(?:[.,]\d+)?)\s*ms", re.IGNORECASE)


class PingError(RuntimeError):
    """No usable ICMP mechanism was found on this machine."""


_mode: str | None = None


def current_mode() -> str | None:
    """The ping mechanism detected so far, or None before the first ping."""
    return _mode


def reset_mode() -> None:
    """Forget the detected mechanism (mainly for tests)."""
    global _mode
    _mode = None


def resolve_mode() -> str:
    """Detect and cache the working ping mechanism.

    The probe pings the loopback address, so detection never touches the
    network and costs at most a few milliseconds.
    """
    global _mode
    if _mode is None:
        _mode = _detect_mode()
    return _mode


def _detect_mode() -> str:
    try:
        _icmp_once(
            _LOOPBACK,
            privileged=False,
            timeout=_PROBE_TIMEOUT,
            payload_size=_PROBE_PAYLOAD_SIZE,
        )
        return MODE_ICMP_UNPRIVILEGED
    except SocketPermissionError:
        pass

    try:
        _icmp_once(
            _LOOPBACK,
            privileged=True,
            timeout=_PROBE_TIMEOUT,
            payload_size=_PROBE_PAYLOAD_SIZE,
        )
        return MODE_ICMP_PRIVILEGED
    except SocketPermissionError:
        pass

    if _system_once(_LOOPBACK, _PROBE_TIMEOUT, _PROBE_PAYLOAD_SIZE) is not None:
        return MODE_SYSTEM_PING

    raise PingError(
        "No working ping mechanism on this machine (unprivileged ICMP, "
        "privileged ICMP and the system ping binary all failed). "
        'On Linux run: sysctl -w net.ipv4.ping_group_range="0 2147483647" '
        "or use an account with root privileges."
    )


def resolve_concurrency() -> int:
    """The parallel-ping concurrency from ``MXL_PING_CONCURRENCY``.

    Shared by the CLI and the GUI. Unset or invalid values fall back to
    ``DEFAULT_CONCURRENCY``; anything above ``MAX_CONCURRENCY`` is clamped.
    """
    raw = os.environ.get(CONCURRENCY_ENV, "")
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_CONCURRENCY
    if parsed < 1:
        return DEFAULT_CONCURRENCY
    return min(parsed, MAX_CONCURRENCY)


def ping_server(
    server: GameServer,
    tries: int,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    payload_size: int = DEFAULT_PAYLOAD_SIZE,
    on_attempt: Callable[[int, float | None], None] | None = None,
) -> list[float | None]:
    """Ping one server sequentially and return one entry per attempt.

    Entries are round-trip times in milliseconds, or None for attempts
    that failed or timed out. ``on_attempt`` is called after every attempt
    with the 1-based attempt number, so drivers can print live progress.
    """
    if tries < 1:
        raise ValueError("tries must be at least 1")

    mode = resolve_mode()
    results: list[float | None] = []
    for attempt in range(1, tries + 1):
        if mode == MODE_SYSTEM_PING:
            rtt = _system_once(server.ip, timeout, payload_size)
        else:
            rtt = _icmp_once(
                server.ip,
                privileged=(mode == MODE_ICMP_PRIVILEGED),
                timeout=timeout,
                payload_size=payload_size,
            )
        results.append(rtt)
        if on_attempt is not None:
            on_attempt(attempt, rtt)
    return results


def ping_servers(
    servers: Sequence[GameServer],
    tries: int,
    *,
    concurrency: int = DEFAULT_CONCURRENCY,
    timeout: float = DEFAULT_TIMEOUT,
    payload_size: int = DEFAULT_PAYLOAD_SIZE,
    stop: threading.Event | None = None,
    on_server_start: Callable[[GameServer], None] | None = None,
    on_server_done: Callable[[GameServer, list[float | None]], None] | None = None,
) -> list[list[float | None]]:
    """Ping several servers at once and return one result list per server.

    The returned lists are in the same order as ``servers``, no matter in
    which order the servers finish. Callbacks are invoked from worker
    threads but serialized through a lock, so drivers can print from them
    without garbling lines. ``on_server_done`` receives the server and its
    ping list. A worker that fails unexpectedly is treated as a server
    that did not answer (all attempts None) rather than crashing the run.

    ``stop`` lets a driver cancel the run: servers that have not started
    yet are reported as all-None as soon as the event is set (servers
    already in flight finish their current attempts). Done callbacks fire
    for those skipped servers too, so callers always get a complete
    result set.
    """
    if tries < 1:
        raise ValueError("tries must be at least 1")
    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    if not servers:
        return []

    results: list[list[float | None] | None] = [None] * len(servers)
    lock = threading.Lock()

    def _run(index: int, server: GameServer) -> None:
        if stop is not None and stop.is_set():
            pings = [None] * tries
        else:
            with lock:
                if on_server_start is not None:
                    on_server_start(server)
            try:
                pings = ping_server(
                    server, tries, timeout=timeout, payload_size=payload_size
                )
            except Exception:
                pings = [None] * tries
        results[index] = pings
        with lock:
            if on_server_done is not None:
                on_server_done(server, pings)

    workers = min(concurrency, len(servers))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run, index, server) for index, server in enumerate(servers)]
        for future in futures:
            future.result()
    return [pings if pings is not None else [None] * tries for pings in results]


def _icmp_once(
    host: str,
    *,
    privileged: bool,
    timeout: float,
    payload_size: int,
) -> float | None:
    """One ICMP attempt via icmplib. Raises SocketPermissionError upward."""
    try:
        result = icmplib.ping(
            host,
            count=1,
            timeout=timeout,
            payload_size=payload_size,
            privileged=privileged,
        )
    except SocketPermissionError:
        raise
    except ICMPLibError:
        # Lookup failure, unreachable host, socket hiccup: a failed attempt.
        return None
    if not result.is_alive:
        return None
    return result.avg_rtt


def _system_once(host: str, timeout: float, payload_size: int) -> float | None:
    """One ICMP attempt via the system ping binary."""
    try:
        completed = subprocess.run(
            _system_ping_args(host, timeout, payload_size),
            capture_output=True,
            text=True,
            timeout=timeout + 2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return _parse_ping_output(completed.stdout)


def _system_ping_args(host: str, timeout: float, payload_size: int) -> list[str]:
    system = platform.system()
    if system == "Windows":
        return [
            "ping",
            "-n",
            "1",
            "-w",
            str(int(timeout * 1000)),
            "-l",
            str(payload_size),
            host,
        ]
    if system == "Darwin":
        return ["ping", "-c", "1", "-t", str(int(timeout)), "-s", str(payload_size), host]
    return ["ping", "-c", "1", "-W", str(int(timeout)), "-s", str(payload_size), host]


def _parse_ping_output(output: str) -> float | None:
    """Extract a round-trip time in ms from ping output; None if absent.

    The strict pattern matches the English "time=23.4 ms" line used by
    Linux, macOS and Windows. The summary pattern matches the Linux/macOS
    final statistics line, which some iputils builds emit without any
    per-reply "time=" field. The loose pattern is a last-resort fallback
    for localized output (e.g. "temps=23,5 ms" on French systems); with a
    single packet every "N ms" value in the output is the same RTT.
    """
    match = _TIME_PATTERN.search(output)
    if match is None:
        match = _RTT_SUMMARY_PATTERN.search(output)
    if match is None:
        match = _LOOSE_PATTERN.search(output)
    if match is None:
        return None
    return float(match.group(1).replace(",", "."))
