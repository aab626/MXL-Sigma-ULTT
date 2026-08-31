# MXL Sigma (Unofficial) Lag Test Tool

A small multi-platform app I made for the Median XL Sigma community. More info here: [forum thread](https://forum.median-xl.com/viewtopic.php?f=4&t=24270).
Pings every GS and shows the latency to each one, so you can pick the least laggy to play on.

You can find the old version on the [releases page: v1.1](https://github.com/aab626/MXL-Sigma-ULTT/releases/tag/1.1).

## Downloads

Grab the latest binary from the [releases page](https://github.com/drizak/MXL-Sigma-ULTT/releases). Each release ships one build per platform: `windows`, `linux`, `macos`. Choose wisely!

Since the binaries are not code-signed, your OS may complain the first time you run one:
- **macOS**: Gatekeeper will refuse to open an unsigned binary. To fix it: run `xattr -d com.apple.quarantine <path/to/binary>`, `chmod +x` may be needed.
- **Linux**: just `chmod +x` it if needed.

## Usage

Just open the app and:

1. **Tries per server**: Set the number of tries per server. More tries means a more reliable measurement. A good default is 4.
2. **Region**: Set your desired region, of `All` if you want to test the whole wide world :)
3. **Start Scan**: Just press the big button 🚀

Each server reports the `min`, `max`, `avg` (average) and `StdDev` (standard deviation) of all measures within a GS. A good server ideally has low `min` latency, and a close to 0 or 1 `StdDev`.
With tries set to 1 the `StdDev` cannot be computed, use that only for a quick reachability test.

### Pinging methods
On a more technical note, the footer shows which ping mode ended up in use (`icmp-unprivileged`, `icmp-privileged` or `system-ping`):

- `icmp-unprivileged`: `icmplib` library uses a plain ICMP datagram socket, no special rights needed. Works on Windows/macOS by default, and on Linux if the kernel allows it.
- `icmp-privileged`: `icmplib` with a raw ICMP socket. Requires rights.
- `system-ping`: Falls back to shelling out to the OS's own ping binary (`setuid`/`setcap` on most distros, so it works for any user).

> **What does this means?** If you see `system-ping`, your machine didn't allow _unprivileged_ `ICMP` and the app worked around it via the system binary; `icmp-unprivileged` is the normal/fast path. If all three fail, the scan errors out with a hint to set ping_group_range.

## Building from source

The project uses [uv](https://docs.astral.sh/uv/) and Python 3.12:

```
uv sync
uv run python -m gui          # the GUI, run from source
uv run python -m core         # the old terminal UI, run from source
uv run pytest                 # tests
uv run ruff check .           # lint
```

The server list URL is deliberately not stored anywhere in this repository (Median XL admin request).
For a dev checkout, copy `.env.example` to `.env` and point `GS_LIST_URL` at the game server list the release binaries use.

To build a release binary (requires the same `.env`):

```
uv run python scripts/build.py
```

This bakes the URL into the build and produces a single-file windowed executable in `dist/`. 
