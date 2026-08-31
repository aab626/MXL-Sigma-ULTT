import subprocess
import threading
import time

import pytest
from icmplib.exceptions import ICMPLibError, SocketPermissionError

import core.pinger as pinger
from core.gslist import GameServer
from core.pinger import (
    MODE_ICMP_PRIVILEGED,
    MODE_ICMP_UNPRIVILEGED,
    MODE_SYSTEM_PING,
    PingError,
)

SERVER = GameServer(name="GS1", label="Test [us]", country_code="us", ip="192.0.2.10")


@pytest.fixture(autouse=True)
def _fresh_mode():
    pinger.reset_mode()
    yield
    pinger.reset_mode()


def test_parse_linux_output():
    output = "rtt min/avg/max/mdev = 0.168/0.168/0.168/0.000 ms"
    assert pinger._parse_ping_output("time=23.4 ms\n" + output) == 23.4


def test_parse_windows_output():
    output = "Reply from 192.0.2.10: bytes=32 time=23ms TTL=54"
    assert pinger._parse_ping_output(output) == 23.0


def test_parse_windows_sub_millisecond():
    assert pinger._parse_ping_output("Reply from 192.0.2.10: bytes=32 time<1ms TTL=54") == 1.0


def test_parse_localized_output_fallback():
    assert pinger._parse_ping_output("temps=23 ms TTL=54") == 23.0
    assert pinger._parse_ping_output("temps=23,5 ms TTL=54") == 23.5
    assert pinger._parse_ping_output("Minimum = 3ms, Maximum = 3ms") == 3.0


def test_parse_output_without_times():
    assert pinger._parse_ping_output("Request timed out.") is None
    assert pinger._parse_ping_output("") is None


def test_parse_linux_summary_line_without_time_field():
    output = (
        "PING 127.0.0.1 (127.0.0.1) 8(36) bytes of data.\n"
        "16 bytes from 127.0.0.1: icmp_seq=1 ttl=64\n\n"
        "--- 127.0.0.1 ping statistics ---\n"
        "1 packets transmitted, 1 received, 0% packet loss, time 0ms\n"
        "rtt min/avg/max/mdev = 0.168/0.168/0.168/0.000 ms\n"
    )
    assert pinger._parse_ping_output(output) == 0.168


@pytest.mark.parametrize(
    ("system", "expected"),
    [
        ("Windows", ["ping", "-n", "1", "-w", "2000", "-l", "32", "192.0.2.10"]),
        ("Darwin", ["ping", "-c", "1", "-t", "2", "-s", "32", "192.0.2.10"]),
        ("Linux", ["ping", "-c", "1", "-W", "2", "-s", "32", "192.0.2.10"]),
    ],
)
def test_system_ping_args_per_platform(system, expected, monkeypatch):
    monkeypatch.setattr(pinger.platform, "system", lambda: system)
    assert pinger._system_ping_args("192.0.2.10", 2.0, 32) == expected


def test_system_once_missing_binary(monkeypatch):
    def raise_missing(*args, **kwargs):
        raise FileNotFoundError("no ping binary")

    monkeypatch.setattr(pinger.subprocess, "run", raise_missing)
    assert pinger._system_once("192.0.2.10", 2.0, 32) is None


def test_system_once_timeout(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ping", timeout=4)

    monkeypatch.setattr(pinger.subprocess, "run", raise_timeout)
    assert pinger._system_once("192.0.2.10", 2.0, 32) is None


def test_detect_prefers_unprivileged(monkeypatch):
    calls: list[bool] = []

    def fake_icmp_once(host, *, privileged, timeout, payload_size):
        calls.append(privileged)
        return 0.2

    monkeypatch.setattr(pinger, "_icmp_once", fake_icmp_once)
    assert pinger.resolve_mode() == MODE_ICMP_UNPRIVILEGED
    assert calls == [False]
    assert pinger.current_mode() == MODE_ICMP_UNPRIVILEGED


def test_detect_falls_back_to_privileged(monkeypatch):
    def fake_icmp_once(host, *, privileged, timeout, payload_size):
        if not privileged:
            raise SocketPermissionError("denied")
        return 0.2

    monkeypatch.setattr(pinger, "_icmp_once", fake_icmp_once)
    assert pinger.resolve_mode() == MODE_ICMP_PRIVILEGED


def test_detect_falls_back_to_system_ping(monkeypatch):
    def fake_icmp_once(host, *, privileged, timeout, payload_size):
        raise SocketPermissionError("denied")

    monkeypatch.setattr(pinger, "_icmp_once", fake_icmp_once)
    monkeypatch.setattr(pinger, "_system_once", lambda host, timeout, size: 0.5)
    assert pinger.resolve_mode() == MODE_SYSTEM_PING


def test_detect_raises_when_nothing_works(monkeypatch):
    def fake_icmp_once(host, *, privileged, timeout, payload_size):
        raise SocketPermissionError("denied")

    monkeypatch.setattr(pinger, "_icmp_once", fake_icmp_once)
    monkeypatch.setattr(pinger, "_system_once", lambda host, timeout, size: None)
    with pytest.raises(PingError):
        pinger.resolve_mode()


def test_ping_server_collects_all_attempts(monkeypatch):
    monkeypatch.setattr(pinger, "resolve_mode", lambda: MODE_ICMP_UNPRIVILEGED)
    sequence = iter([0.5, None, 2.0, 1.25])
    seen_hosts: list[str] = []

    def fake_icmp_once(host, *, privileged, timeout, payload_size):
        seen_hosts.append(host)
        assert privileged is False
        assert timeout == 2.0
        assert payload_size == 32
        return next(sequence)

    monkeypatch.setattr(pinger, "_icmp_once", fake_icmp_once)
    results = pinger.ping_server(SERVER, tries=4)
    assert results == [0.5, None, 2.0, 1.25]
    assert seen_hosts == ["192.0.2.10"] * 4


def test_ping_server_reports_attempts_live(monkeypatch):
    monkeypatch.setattr(pinger, "resolve_mode", lambda: MODE_ICMP_UNPRIVILEGED)
    sequence = iter([0.5, None])
    monkeypatch.setattr(
        pinger,
        "_icmp_once",
        lambda host, *, privileged, timeout, payload_size: next(sequence),
    )
    events: list[tuple[int, float | None]] = []
    pinger.ping_server(SERVER, tries=2, on_attempt=lambda n, rtt: events.append((n, rtt)))
    assert events == [(1, 0.5), (2, None)]


def test_ping_server_uses_system_mode(monkeypatch):
    monkeypatch.setattr(pinger, "resolve_mode", lambda: MODE_SYSTEM_PING)
    calls: list[tuple[str, float, int]] = []

    def fake_system_once(host, timeout, payload_size):
        calls.append((host, timeout, payload_size))
        return 42.0 if host == "192.0.2.10" else None

    monkeypatch.setattr(pinger, "_system_once", fake_system_once)
    results = pinger.ping_server(SERVER, tries=2, timeout=3.0, payload_size=64)
    assert results == [42.0, 42.0]
    assert calls == [("192.0.2.10", 3.0, 64)] * 2


def test_ping_server_uses_privileged_mode(monkeypatch):
    monkeypatch.setattr(pinger, "resolve_mode", lambda: MODE_ICMP_PRIVILEGED)
    flags: list[bool] = []

    def fake_icmp_once(host, *, privileged, timeout, payload_size):
        flags.append(privileged)
        return 0.1

    monkeypatch.setattr(pinger, "_icmp_once", fake_icmp_once)
    assert pinger.ping_server(SERVER, tries=1) == [0.1]
    assert flags == [True]


def test_ping_server_rejects_zero_tries():
    with pytest.raises(ValueError):
        pinger.ping_server(SERVER, tries=0)


def test_icmp_once_maps_generic_icmplib_errors_to_none(monkeypatch):
    def raise_generic(*args, **kwargs):
        raise ICMPLibError("boom")

    monkeypatch.setattr(pinger.icmplib, "ping", raise_generic)
    assert (
        pinger._icmp_once("192.0.2.10", privileged=False, timeout=2.0, payload_size=32)
        is None
    )


def test_icmp_once_lets_permission_errors_through(monkeypatch):
    def raise_permission(*args, **kwargs):
        raise SocketPermissionError("denied")

    monkeypatch.setattr(pinger.icmplib, "ping", raise_permission)
    with pytest.raises(SocketPermissionError):
        pinger._icmp_once("192.0.2.10", privileged=False, timeout=2.0, payload_size=32)


def test_mode_is_cached(monkeypatch):
    calls: list[int] = []

    def fake_detect_mode():
        calls.append(1)
        return MODE_ICMP_UNPRIVILEGED

    monkeypatch.setattr(pinger, "_detect_mode", fake_detect_mode)
    assert pinger.resolve_mode() == MODE_ICMP_UNPRIVILEGED
    assert pinger.resolve_mode() == MODE_ICMP_UNPRIVILEGED
    assert len(calls) == 1


def _servers(count):
    return [
        GameServer(
            name=f"GS{index}",
            label="Test [us]",
            country_code="us",
            ip=f"192.0.2.{index}",
        )
        for index in range(1, count + 1)
    ]


def test_ping_servers_preserves_order(monkeypatch):
    def fake_ping(server, tries, timeout=2.0, payload_size=32):
        return [float(server.name[2:])] * tries

    monkeypatch.setattr(pinger, "ping_server", fake_ping)
    servers = _servers(8)
    results = pinger.ping_servers(servers, 2, concurrency=4)
    assert [pings[0] for pings in results] == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]


def test_ping_servers_respects_concurrency_cap(monkeypatch):
    lock = threading.Lock()
    state = {"current": 0, "peak": 0}

    def fake_ping(server, tries, timeout=2.0, payload_size=32):
        with lock:
            state["current"] += 1
            state["peak"] = max(state["peak"], state["current"])
        time.sleep(0.05)
        with lock:
            state["current"] -= 1
        return [1.0] * tries

    monkeypatch.setattr(pinger, "ping_server", fake_ping)
    pinger.ping_servers(_servers(8), 2, concurrency=3)
    assert state["peak"] == 3


def test_ping_servers_sequential_when_concurrency_one(monkeypatch):
    lock = threading.Lock()
    state = {"current": 0, "peak": 0}

    def fake_ping(server, tries, timeout=2.0, payload_size=32):
        with lock:
            state["current"] += 1
            state["peak"] = max(state["peak"], state["current"])
        with lock:
            state["current"] -= 1
        return [1.0] * tries

    monkeypatch.setattr(pinger, "ping_server", fake_ping)
    pinger.ping_servers(_servers(4), 2, concurrency=1)
    assert state["peak"] == 1


def test_ping_servers_empty_list():
    assert pinger.ping_servers([], 4) == []


def test_ping_servers_worker_crash_becomes_failures(monkeypatch):
    def crashing_ping(server, tries, timeout=2.0, payload_size=32):
        raise RuntimeError("boom")

    monkeypatch.setattr(pinger, "ping_server", crashing_ping)
    results = pinger.ping_servers(_servers(3), 4, concurrency=2)
    assert results == [[None] * 4, [None] * 4, [None] * 4]


def test_ping_servers_callbacks_fire_once_per_server(monkeypatch):
    def fake_ping(server, tries, timeout=2.0, payload_size=32):
        return [0.5] * tries

    monkeypatch.setattr(pinger, "ping_server", fake_ping)
    servers = _servers(5)
    started: list[str] = []
    done: list[tuple[str, list]] = []
    pinger.ping_servers(
        servers,
        2,
        concurrency=3,
        on_server_start=lambda server: started.append(server.name),
        on_server_done=lambda server, pings: done.append((server.name, pings)),
    )
    assert sorted(started) == sorted(server.name for server in servers)
    assert sorted(name for name, _ in done) == sorted(server.name for server in servers)
    assert all(pings == [0.5, 0.5] for _, pings in done)


def test_ping_servers_validates_arguments(monkeypatch):
    with pytest.raises(ValueError):
        pinger.ping_servers(_servers(1), 0)
    with pytest.raises(ValueError):
        pinger.ping_servers(_servers(1), 4, concurrency=0)


def test_ping_servers_stop_before_start(monkeypatch):
    pinged: list[str] = []

    def fake_ping(server, tries, timeout=2.0, payload_size=32):
        pinged.append(server.name)
        return [1.0] * tries

    monkeypatch.setattr(pinger, "ping_server", fake_ping)
    stop = threading.Event()
    stop.set()
    results = pinger.ping_servers(_servers(3), 2, concurrency=2, stop=stop)
    assert pinged == []
    assert results == [[None, None]] * 3


def test_ping_servers_stop_midway(monkeypatch):
    pinged: list[str] = []

    def fake_ping(server, tries, timeout=2.0, payload_size=32):
        pinged.append(server.name)
        return [1.0] * tries

    monkeypatch.setattr(pinger, "ping_server", fake_ping)
    stop = threading.Event()
    servers = _servers(3)
    results = pinger.ping_servers(
        servers,
        2,
        concurrency=1,
        stop=stop,
        on_server_done=lambda server, _pings: stop.set(),
    )
    assert pinged == [servers[0].name]
    assert results[0] == [1.0, 1.0]
    assert results[1] == [None, None]
    assert results[2] == [None, None]


def test_resolve_concurrency(monkeypatch):
    monkeypatch.delenv(pinger.CONCURRENCY_ENV, raising=False)
    assert pinger.resolve_concurrency() == pinger.DEFAULT_CONCURRENCY
    monkeypatch.setenv(pinger.CONCURRENCY_ENV, "3")
    assert pinger.resolve_concurrency() == 3
    monkeypatch.setenv(pinger.CONCURRENCY_ENV, "1")
    assert pinger.resolve_concurrency() == 1
    monkeypatch.setenv(pinger.CONCURRENCY_ENV, "999")
    assert pinger.resolve_concurrency() == pinger.MAX_CONCURRENCY
    for bad in ("0", "-2", "abc", ""):
        monkeypatch.setenv(pinger.CONCURRENCY_ENV, bad)
        assert pinger.resolve_concurrency() == pinger.DEFAULT_CONCURRENCY
