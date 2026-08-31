from pathlib import Path

from core.gslist import (
    GameServer,
    Region,
    extract_country_code,
    fetch_gs_list,
    filter_servers,
    invalid_tokens,
    parse_gs_list,
    regions_for,
    unknown_country_codes,
)

FIXTURE = Path(__file__).parent / "fixtures" / "gs_list_fake.dat"


def load_servers() -> list[GameServer]:
    return parse_gs_list(FIXTURE.read_text(encoding="utf-8"))


def test_parse_reads_all_fields():
    servers = load_servers()
    assert len(servers) == 6
    first = servers[0]
    assert first.name == "GS1"
    assert first.label == "America [us]"
    assert first.country_code == "us"
    assert first.ip == "192.0.2.10"


def test_parse_skips_blank_and_broken_lines():
    names = [server.name for server in load_servers()]
    assert "GS7" not in names
    assert all(server.ip for server in load_servers())


def test_extract_country_code():
    assert extract_country_code("America [us]") == "us"
    assert extract_country_code("Upper [DE]") == "de"
    assert extract_country_code("No tag here") == ""


def test_regions_multi_region():
    assert regions_for("ru") == {Region.EUROPE, Region.ASIA}
    assert regions_for("us") == {Region.NORTH_AMERICA}
    assert regions_for("xx") == set()


def test_unknown_country_codes():
    assert unknown_country_codes(load_servers()) == {"xx"}


def test_filter_by_country_code():
    servers = load_servers()
    assert [s.name for s in filter_servers(servers, ["us"])] == ["GS1"]


def test_filter_alias_uk_matches_gb():
    servers = load_servers()
    assert [s.name for s in filter_servers(servers, ["uk"])] == ["GS5"]


def test_filter_by_keyword_includes_multi_region():
    servers = load_servers()
    assert {s.name for s in filter_servers(servers, ["asia"])} == {"GS3", "GS6"}


def test_filter_empty_tokens_returns_all():
    servers = load_servers()
    assert filter_servers(servers, []) == servers
    assert filter_servers(servers, ["   "]) == servers


def test_filter_multiple_tokens_has_no_duplicates():
    names = [s.name for s in filter_servers(load_servers(), ["us", "europe"])]
    assert len(names) == len(set(names))
    assert set(names) == {"GS1", "GS2", "GS3", "GS5"}


def test_filter_no_match():
    assert filter_servers(load_servers(), ["ke"]) == []


def test_invalid_tokens():
    assert invalid_tokens(load_servers(), ["us", "bogus", "ASIA"]) == ["bogus"]


def test_fetch_reads_local_file():
    assert "GS1" in fetch_gs_list(FIXTURE.as_uri())
