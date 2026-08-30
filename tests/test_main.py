from core.__main__ import _parse_tokens, _parse_tries


def test_parse_tries():
    assert _parse_tries("4") == 4
    assert _parse_tries("0") == 0
    assert _parse_tries("abc") is None
    assert _parse_tries("3.5") is None
    assert _parse_tries(" 7 ") == 7


def test_parse_tokens():
    assert _parse_tokens("us de") == ["us", "de"]
    assert _parse_tokens("us, de") == ["us", "de"]
    assert _parse_tokens("  ") == []
    assert _parse_tokens("") == []
    assert _parse_tokens("EUROPE") == ["EUROPE"]
