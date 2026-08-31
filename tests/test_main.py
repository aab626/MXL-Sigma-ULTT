import core.__main__ as cli
from core.__main__ import _parse_concurrency, _parse_tokens, _parse_tries
from core.pinger import DEFAULT_CONCURRENCY


def test_parse_tries():
    assert _parse_tries("4") == 4
    assert _parse_tries("0") == 0
    assert _parse_tries("abc") is None
    assert _parse_tries("3.5") is None
    assert _parse_tries(" 7 ") == 7


def test_parse_concurrency():
    assert _parse_concurrency("6") == 6
    assert _parse_concurrency("1") == 1
    assert _parse_concurrency("0") == 0
    assert _parse_concurrency("abc") is None
    assert _parse_concurrency("") is None


def test_concurrency_from_env(monkeypatch):
    monkeypatch.delenv("MXL_PING_CONCURRENCY", raising=False)
    assert cli._concurrency_from_env() == DEFAULT_CONCURRENCY
    monkeypatch.setenv("MXL_PING_CONCURRENCY", "3")
    assert cli._concurrency_from_env() == 3
    monkeypatch.setenv("MXL_PING_CONCURRENCY", "0")
    assert cli._concurrency_from_env() == DEFAULT_CONCURRENCY
    monkeypatch.setenv("MXL_PING_CONCURRENCY", "abc")
    assert cli._concurrency_from_env() == DEFAULT_CONCURRENCY
    monkeypatch.setenv("MXL_PING_CONCURRENCY", "999")
    assert cli._concurrency_from_env() == 16
    monkeypatch.setenv("MXL_PING_CONCURRENCY", "1")
    assert cli._concurrency_from_env() == 1


def test_parse_tokens():
    assert _parse_tokens("us de") == ["us", "de"]
    assert _parse_tokens("us, de") == ["us", "de"]
    assert _parse_tokens("  ") == []
    assert _parse_tokens("") == []
    assert _parse_tokens("EUROPE") == ["EUROPE"]
