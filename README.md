# MXL Sigma (Unofficial) Lag Test Tool

A small tool that pings every Median XL Sigma game server and prints a latency report, so you can pick the least laggy GS to play on.

This is the v2 rewrite: it now runs on Windows, Linux and macOS, and the report prints straight to your terminal instead of a text file. It is not affiliated with or endorsed by the Sigma team.

## Downloads

Grab the latest binary from the [releases page](https://github.com/drizak/MXL-Sigma-ULTT/releases). Each release ships one build per platform: `windows`, `linux`, `macos`.

Since the binaries are not code-signed, your OS may complain the first time you run one:

- **Windows**: SmartScreen will warn you ("Windows protected your PC"). Click *More info* → *Run anyway*.
- **macOS**: Gatekeeper will refuse to open an unsigned binary. After downloading, run `xattr -d com.apple.quarantine <binary>`, or launch it once, dismiss the block dialog, then allow it under System Settings → Privacy & Security (Open Anyway). On recent macOS versions right-click → Open in Finder no longer works.
- **Linux**: just `chmod +x` it if needed.

## Usage

Run the program and answer two prompts:

1. **Tries per server** — how many pings to send at each GS, 1 to 10. More tries means a more reliable measurement. Leave blank for the default (4).
2. **Filter** — a country code (`us`, `de`, ...) or a region keyword (`europe`, `asia`, `northamerica`, `southamerica`, `oceania`, `africa`). Leave blank to test everything. Servers from unknown countries are always tested and flagged.

The report prints to the screen: min/max/avg/standard deviation per server, a Top 5, and an "unstable" tag for servers with a standard deviation above 10 ms. A server that never answers shows up as SKIPPED.

Servers are pinged in parallel, 6 at a time by default. Set the `MXL_PING_CONCURRENCY` environment variable to change that (for example `MXL_PING_CONCURRENCY=1` gives you the old one-server-at-a-time behavior).

Two things worth knowing:

- GS 6 almost never responds to pings. Expect it to be skipped.
- With tries set to 1 there is nothing to compute a standard deviation (or average) from, so that mode is only useful for a quick reachability check.

## Ping permissions

ICMP is a privileged operation on some systems. How this affects you:

- **Windows**: nothing to do, plain users can ping.
- **macOS**: works out of the box.
- **Linux**: an unprivileged user needs the kernel to allow ICMP echo sockets, either via `sysctl net.ipv4.ping_group_range="0 2147483647"`, or by running the tool as root. If neither applies, the tool falls back to your system's `ping` binary automatically.

The banner shows which ping mode ended up in use (`icmp-unprivileged`, `icmp-privileged` or `system-ping`).

## Building from source

The project uses [uv](https://docs.astral.sh/uv/) and Python 3.12:

```
uv sync
uv run python -m core        # run from source
uv run pytest                # tests
uv run ruff check .          # lint
```

The server list URL is deliberately not stored anywhere in this repository. For a dev checkout, copy `.env.example` to `.env` and point `GS_LIST_URL` at the game server list the release binaries use. The URL ships baked into every released binary, so it isn't hard to come by — ask in the forum topic or on Discord if you need it. A test in the suite fails if the URL ever ends up in a trackable file, so please keep it out.

To build a release binary (requires the same `.env`):

```
uv run python scripts/build.py
```

This bakes the URL into the build and produces a single-file executable in `dist/`. Never commit your `.env`.

## Development

Design notes, phase-by-phase decisions and the reasoning behind them live in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Credits and license

Made by *Drizak for the Median XL Sigma community. Feedback: post in the [forum topic](https://forum.median-xl.com/viewtopic.php?f=4&t=24270) or find me on Discord: Drizak#2555.

The code in this repo is MIT licensed. It relies on [icmplib](https://github.com/ValentinBELUGOU/icmplib), which is LGPL-3.0 — it stays a separately linked library, and its source remains available at the link above.
