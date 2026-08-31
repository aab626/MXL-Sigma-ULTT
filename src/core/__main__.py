"""Interactive command-line driver.

Flow matches the old tool: banner, tries prompt, fetch, filter prompt,
pings, report on screen. The deliberate differences from the legacy
script are listed in docs/DEVELOPMENT.md.
"""

import os
import re
import urllib.error
from importlib.metadata import PackageNotFoundError, version

from core.config import ConfigError, get_gs_list_url
from core.gslist import (
    GameServer,
    Region,
    fetch_gs_list,
    filter_servers,
    invalid_tokens,
    parse_gs_list,
)
from core.output import ServerResult, collect, render_report
from core.pinger import (
    DEFAULT_CONCURRENCY,
    PingError,
    ping_servers,
    resolve_mode,
)

_BANNER = "MEDIAN XL SIGMA TSW Unofficial Lag Test Tool by *Drizak"
_TOKEN_SPLIT = re.compile(r"[\s,]+")
_CONCURRENCY_ENV = "MXL_PING_CONCURRENCY"
_MAX_CONCURRENCY = 16


def main() -> int:
    print(_BANNER)
    print(f"version: {_version()}")
    print()

    print("Enter number of tries per server, more pings means more precise measuring.")
    print("Leave blank if not sure (default=4, min=1, max=10).")
    tries = _prompt_tries()
    print(f"Starting operation with {tries} tries.")
    print()

    try:
        url = get_gs_list_url()
    except ConfigError as error:
        print(error)
        return 1

    print("Fetching server list...")
    try:
        text = fetch_gs_list(url)
    except (urllib.error.URLError, OSError, ValueError) as error:
        print(f"Could not fetch the server list: {error}")
        return 1

    servers = parse_gs_list(text)
    if not servers:
        print("The server list is empty.")
        return 1
    print(f"{len(servers)} game servers found.")

    selected = _prompt_filter(servers)
    print()
    print(f"Operation configured to start with {tries} tries.")
    print()

    try:
        mode = resolve_mode()
    except PingError as error:
        print(error)
        return 1
    print(f"Ping mode: {mode}")

    concurrency = _concurrency_from_env()
    print(f"Pinging {len(selected)} servers, {concurrency} at a time.")
    print()

    ping_lists = ping_servers(
        selected,
        tries,
        concurrency=concurrency,
        on_server_start=_print_server_start,
    )
    results: list[ServerResult] = [
        collect(server, pings)
        for server, pings in zip(selected, ping_lists, strict=True)
    ]

    print()
    print(render_report(results, tries))
    print()
    print("Operation complete.")
    try:
        input("Press ENTER to exit.")
    except EOFError:
        pass
    return 0


def _print_server_start(server: GameServer) -> None:
    print(f"Pinging: {server.name:<7}{server.label}")


def _concurrency_from_env() -> int:
    raw = os.environ.get(_CONCURRENCY_ENV, "")
    parsed = _parse_concurrency(raw)
    if parsed is None or parsed < 1:
        return DEFAULT_CONCURRENCY
    return min(parsed, _MAX_CONCURRENCY)


def _parse_concurrency(raw: str) -> int | None:
    try:
        return int(raw)
    except ValueError:
        return None


def _prompt_tries() -> int:
    while True:
        raw = input("Tries: ").strip()
        if raw == "":
            return 4
        parsed = _parse_tries(raw)
        if parsed is None:
            print("Please enter a positive integer.")
        elif parsed < 1:
            print("Please enter an integer greater or equal than 1.")
        elif parsed > 10:
            print("Please enter an integer lesser or equal than 10.")
        else:
            return parsed


def _parse_tries(raw: str) -> int | None:
    try:
        return int(raw)
    except ValueError:
        return None


def _prompt_filter(servers: list[GameServer]) -> list[GameServer]:
    keywords = ", ".join(region.value for region in Region)
    print("Enter a country code (us, jp, etc.) or a keyword to filter the server list.")
    print("All keywords and country codes must be separated by spaces or commas.")
    print("Leave blank to ping every available server.")
    print(f"Available keywords (by region): {keywords}.")
    while True:
        tokens = _parse_tokens(input("Filter by: "))
        invalid = invalid_tokens(servers, tokens)
        if invalid:
            print(f"ERROR: {', '.join(invalid)} is not a valid country code or keyword.")
            print("Please try again.")
            continue
        selected = filter_servers(servers, tokens)
        if not selected:
            print("No servers match that filter.")
            continue
        return selected


def _parse_tokens(raw: str) -> list[str]:
    return [token for token in _TOKEN_SPLIT.split(raw) if token]


def _version() -> str:
    try:
        return version("mxl-sigma-ultt")
    except PackageNotFoundError:
        return "dev"


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print()
        print("Aborted.")
        raise SystemExit(130) from None
