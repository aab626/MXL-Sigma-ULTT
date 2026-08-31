import re
import ssl
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

import certifi

_CC_PATTERN = re.compile(r"\[([a-zA-Z]{2})\]")


class Region(Enum):
    NORTH_AMERICA = "northamerica"
    SOUTH_AMERICA = "southamerica"
    EUROPE = "europe"
    ASIA = "asia"
    OCEANIA = "oceania"
    AFRICA = "africa"


_COUNTRY_REGIONS: dict[str, set[Region]] = {
    "us": {Region.NORTH_AMERICA},
    "ca": {Region.NORTH_AMERICA},
    "mx": {Region.NORTH_AMERICA},
    "br": {Region.SOUTH_AMERICA},
    "ar": {Region.SOUTH_AMERICA},
    "cl": {Region.SOUTH_AMERICA},
    "pe": {Region.SOUTH_AMERICA},
    "co": {Region.SOUTH_AMERICA},
    "uy": {Region.SOUTH_AMERICA},
    "de": {Region.EUROPE},
    "cz": {Region.EUROPE},
    "gb": {Region.EUROPE},
    "uk": {Region.EUROPE},
    "pl": {Region.EUROPE},
    "se": {Region.EUROPE},
    "nl": {Region.EUROPE},
    "lv": {Region.EUROPE},
    "fr": {Region.EUROPE},
    "at": {Region.EUROPE},
    "es": {Region.EUROPE},
    "it": {Region.EUROPE},
    "pt": {Region.EUROPE},
    "ie": {Region.EUROPE},
    "ro": {Region.EUROPE},
    "hu": {Region.EUROPE},
    "bg": {Region.EUROPE},
    "ua": {Region.EUROPE},
    "fi": {Region.EUROPE},
    "no": {Region.EUROPE},
    "dk": {Region.EUROPE},
    "ch": {Region.EUROPE},
    "be": {Region.EUROPE},
    "gr": {Region.EUROPE},
    "vn": {Region.ASIA},
    "sg": {Region.ASIA},
    "jp": {Region.ASIA},
    "kr": {Region.ASIA},
    "cn": {Region.ASIA},
    "in": {Region.ASIA},
    "th": {Region.ASIA},
    "hk": {Region.ASIA},
    "tw": {Region.ASIA},
    "mo": {Region.ASIA},
    "my": {Region.ASIA},
    "id": {Region.ASIA},
    "ph": {Region.ASIA},
    "kh": {Region.ASIA},
    "au": {Region.OCEANIA},
    "nz": {Region.OCEANIA},
    "za": {Region.AFRICA},
    "eg": {Region.AFRICA},
    "ma": {Region.AFRICA},
    "ng": {Region.AFRICA},
    "ke": {Region.AFRICA},
    "ru": {Region.EUROPE, Region.ASIA},
    "tr": {Region.EUROPE, Region.ASIA},
    "kz": {Region.EUROPE, Region.ASIA},
    "ge": {Region.EUROPE, Region.ASIA},
    "am": {Region.EUROPE, Region.ASIA},
    "az": {Region.EUROPE, Region.ASIA},
}

REGION_COUNTRIES: dict[Region, frozenset[str]] = {
    region: frozenset(
        cc for cc, regions in _COUNTRY_REGIONS.items() if region in regions
    )
    for region in Region
}

_REGION_BY_KEYWORD = {region.value: region for region in Region}

_COUNTRY_ALIASES = {"uk": "gb"}


@dataclass(frozen=True)
class GameServer:
    name: str
    label: str
    country_code: str
    ip: str


def _ssl_context() -> ssl.SSLContext:
    # Frozen macOS builds have no system CA store to fall back on; certifi's
    # bundle guarantees TLS verification works on every platform. PyInstaller
    # picks up the cacert.pem data file through its certifi hook.
    return ssl.create_default_context(cafile=certifi.where())


def fetch_gs_list(url: str, timeout: float = 10.0) -> str:
    request = urllib.request.Request(
        url, headers={"User-Agent": "MXL-Sigma-ULTT/2.0"}
    )
    with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
        return response.read().decode("utf-8")


def parse_gs_list(text: str) -> list[GameServer]:
    servers = []
    for line in text.splitlines():
        fields = [field for field in line.split("\t") if field]
        if len(fields) < 3:
            continue
        name, label, ip = fields[0], fields[1], fields[2]
        servers.append(GameServer(name, label, extract_country_code(label), ip))
    return servers


def extract_country_code(label: str) -> str:
    match = _CC_PATTERN.search(label)
    return match.group(1).lower() if match else ""


def regions_for(country_code: str) -> set[Region]:
    return _COUNTRY_REGIONS.get(country_code, set())


def unknown_country_codes(servers: Iterable[GameServer]) -> set[str]:
    return {
        server.country_code
        for server in servers
        if server.country_code and server.country_code not in _COUNTRY_REGIONS
    }


def normalize_token(token: str) -> str:
    return token.strip().lower()


def filter_servers(
    servers: list[GameServer], tokens: Iterable[str]
) -> list[GameServer]:
    normalized = [t for t in (normalize_token(token) for token in tokens) if t]
    if not normalized:
        return list(servers)
    return [server for server in servers if any(_matches(server, t) for t in normalized)]


def invalid_tokens(servers: list[GameServer], tokens: Iterable[str]) -> list[str]:
    observed = {server.country_code for server in servers if server.country_code}
    known = observed | set(_COUNTRY_REGIONS) | set(_REGION_BY_KEYWORD)
    return [
        t for t in (normalize_token(token) for token in tokens) if t and t not in known
    ]


def _matches(server: GameServer, token: str) -> bool:
    if len(token) == 2:
        return _canonical(token) == _canonical(server.country_code)
    region = _REGION_BY_KEYWORD.get(token)
    return region is not None and region in regions_for(server.country_code)


def _canonical(country_code: str) -> str:
    return _COUNTRY_ALIASES.get(country_code, country_code)
