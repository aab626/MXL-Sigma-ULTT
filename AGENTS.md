# AGENTS.md

## Project

Latency tester for Median XL Sigma game servers: fetches the server list, ICMP-pings every server, renders a latency report. One core package (`src/core`) shared by two frontends: a PySide6 GUI (`src/gui`, the only thing shipped as a binary) and a legacy terminal UI (`python -m core`). Python 3.12, everything through [uv](https://docs.astral.sh/uv/).

The terminal UI is compatibility-only: it exists to keep the old tool's behavior for users who want it. No further support is guaranteed — don't invest in it, don't port new features to it, and route all new functionality through the GUI.

```
src/core/            shared package (both frontends import it)
  config.py          resolves GS_LIST_URL: env → .env → build-baked _baked module
  gslist.py          fetch + parse server list, region model, country→region table
  pinger.py          ICMP with fallback chain, parallel ping pool, concurrency knob
  stats.py           min/max/avg/stddev from a ping list
  output.py          pure string report rendering (no printing)
  __main__.py        terminal UI driver (owns every input()/print())
  _baked.py          GENERATED at build time, gitignored — never hand-write
src/gui/             PySide6 frontend (the only binary that ships)
  window.py          main window, table, chips, ScanWorker wiring
  worker.py          QThread running one scan (fetch → filter → ping)
  theme.py           colors + stylesheet (ACCENT_10/20 pre-blended hex)
  banner.py          banner painted in paintEvent, no image assets
  __main__.py        GUI entry; hidden --smoke flag for the build contract
  assets/fonts/      DM Sans + JetBrains Mono TTFs (only bundled assets)
tests/               pytest, zero network, RFC 5737 sanitized IPs only
scripts/build.py     bakes URL + PyInstaller build + smoke test
.github/workflows/release.yml   v* tags → 3-OS build matrix → release
```

## Commands

- `uv sync` — create/refresh `.venv` (hatchling installs the project editable; if imports break confusingly, re-run this before suspecting anything else)
- `uv run pytest` — full suite; no test may touch the network
- `uv run ruff check .` — lint (line length 100; E/F/W/I/UP/B)
- `uv run python -m gui` / `uv run python -m core` — GUI / terminal UI from source
- `uv run python scripts/build.py` — bake URL + PyInstaller GUI binary into `dist/` (requires `GS_LIST_URL`; `--no-smoke` skips the post-build smoke test)

## The URL secret

- The real server-list URL lives only in `.env` (`GS_LIST_URL`, untracked) or the `GS_LIST_URL` GitHub secret. Copy `.env.example` to `.env`; ask the maintainer for the value. The repo is public and the list host isn't ours to expose.
- `src/core/_baked.py` is generated at build time with the URL folded in. Gitignored; never write it by hand, never commit it. It may exist in a working tree from a previous build. `scripts/build.py` deliberately never reads it back — a stale baked URL must not leak into a fresh build.
- `tests/test_leak_guard.py` scans every git-trackable file for the URL whenever it's configured (env or `.env`) and fails loudly; it skips when no URL is set (fresh clones). In CI the secret makes the scan real. If the URL or any real server IP shows up in a diff, strip it before it lands in git history.
- Tests and fixtures must never contain real server IPs — sanitized data only, using the RFC 5737 documentation ranges.

## Testing quirks

- Zero network in tests: the gslist fetch test reads through a `file://` URL; pinger tests fake the icmplib and subprocess layers; GUI tests patch names inside `gui.worker` and call `ScanWorker.run()` inline for synchronous signals.
- GUI checks are headless (`QT_QPA_PLATFORM=offscreen`). Tests assert structure and wiring, never pixels. For visual checks save `window.grab()` to a PNG — and don't judge cell colors by eye; read them back programmatically (a screenshot once made an average look green on red).

## Non-obvious behavior

- src layout: the importable `core`/`gui` are the installed packages, not stray directories.
- Ping mechanism detection (`core/pinger.py`) tries in order: unprivileged ICMP → privileged ICMP → system `ping` binary; detected once per process via a loopback probe (never touches the network) and cached. The probe uses the real 32-byte payload because some iputils builds suppress `time=` for tiny payloads.
- System-ping output parses tolerantly: strict `time=`, then the `rtt min/avg/max/mdev` summary line, then a loose `N ms` pattern for localized output (e.g. French). The loose pattern is safe only because pings use count=1.
- Failed ping attempts are recorded as `None` and excluded from stats; a server is ERR only when every attempt failed, partial loss shows as "(n/m lost)". Stddev uses `statistics.pstdev` (true mean) — a deliberate break from the old tool's rounded-average quirk.
- `MXL_PING_CONCURRENCY` env var controls parallel pinging via `core.pinger.resolve_concurrency()`: default 6, clamped to 16, `1` reproduces the old sequential behavior. One knob for both frontends.
- `theme.py` pre-blends the orange accent at 10%/20% into `ACCENT_10`/`ACCENT_20` hex constants (Qt rgba() backgrounds don't blend reliably across platforms). Change the accent → re-blend those two by hand.
- Fonts (DM Sans, JetBrains Mono variable TTFs) are the only bundled assets; PyInstaller packs them via `--add-data` and the loader looks in `sys._MEIPASS` when frozen. A missing font fails silently (system fallback), so the smoke test can't catch it.

## Release

- `.github/workflows/release.yml` triggers on `v*` tags only. Each matrix leg (Windows/Linux/macOS) runs the full test suite, then builds; the release job attaches binaries only when all three legs pass. Linux CI needs the Qt runtime libs installed (see workflow).
- Binaries are GUI-only; the terminal UI runs from source, no binary.
- GUI smoke contract: the hidden `--smoke` flag builds the real window on the offscreen Qt platform and exits 0. The exit code is the only observable — windowed binaries have no stdout on Windows.
- GitHub Actions are pinned to exact versions (setup-uv stopped publishing major tags over supply-chain concerns). Keep that habit for any new action.

## Releasing a new version

The agent prepares the release but does NOT touch git: no commits, no tags, no pushes. Division of labor:

Agent does:
1. Update `version` in `pyproject.toml` — the single source of truth (the terminal UI shows it via `importlib.metadata`).
2. Run `uv sync` (or `uv lock`) so `uv.lock`'s own entry matches — the only other place the version exists.
3. Run `uv run pytest` and `uv run ruff check .` before calling it done.

Human then runs (in order):
```
git add <files> && git commit -m "..."   # agent leaves all of this to the user
# push, open PR, merge on GitHub website
git checkout master && git pull
git tag vX.Y.Z                 # MUST match pyproject.toml — nothing enforces it
git push origin vX.Y.Z
gh run watch                   # 3-OS build; release binaries attach when green
```
The tag push triggers the 3-OS build; the release page gets `mxl-sigma-ultt-<tag>-<platform>` binaries. The workflow refuses to build without the `GS_LIST_URL` secret.
