# Development notes

This file is the project's memory. It explains how to work on MXL-Sigma-ULTT without needing the chat that planned the rewrite. Anything the code already says clearly stays out of here; this is for instructions, context, and decisions that would otherwise get lost.

## What this project is

A small CLI tool for the Median XL Sigma community. It downloads the game server list, lets the user filter servers by country code or continent keyword, pings each server, and prints a latency report (min, max, avg, stddev, plus a top five). v2 is a rewrite of the original Python 2 `MXLLagtest.py`, which served as the behavioral reference until the port was complete and has since been deleted from the repo.

## Toolchain

Everything runs through [uv](https://docs.astral.sh/uv/). It manages the Python interpreter, the venv, dependencies, and the lockfile, so nobody needs pyenv or a system Python 3.12. The whole workflow:

- `uv sync` creates and refreshes `.venv` from `uv.lock` and `.python-version` (pinned to 3.12)
- `uv run pytest`, `uv run ruff check .`, `uv run python -m core` run inside that venv

The project installs itself into the venv in editable mode (hatchling config in `pyproject.toml`), which is why `python -m core` resolves the `src/core` package. If imports ever break in a confusing way, re-run `uv sync` before suspecting anything else.

## Layout

`src/core/` is the package, `tests/` holds pytest tests with fixtures, `scripts/` holds build tooling. The src layout means the only importable `core` is the installed one, not whatever happens to be lying around in the working directory.

## Files that stay out of git, on purpose

- `.env` holds `GS_LIST_URL`, the address of the real server list. The repo is public and the list host isn't ours to expose, so the URL is deliberately untracked everywhere. For development, copy `.env.example` to `.env` and ask the maintainer for the value.
- `src/core/_baked.py` gets generated at build time with the URL folded in for release binaries. Never write it by hand and never commit it.
- Real server IPs must never appear in tests or fixtures. Test data is sanitized, always.

If the real URL or real IPs ever show up in a diff, stop and strip them before they land in git history.

## Decisions so far

- The package is named `core`. Short, on purpose.
- No `output.txt`. The old tool wrote results to a file; v2 prints to the terminal only.
- Servers get pinged one at a time for now, so the numbers stay comparable with the old tool. Parallel pinging is on the backlog for after the rewrite.
- The UI is a plain interactive CLI. A Textual TUI comes later, designed from an existing Figma mock.

## Phase 1 notes: the data layer

The data layer lives in three modules. `config.py` resolves the server list URL: it checks the `GS_LIST_URL` environment variable (after loading `.env` if present), then falls back to the build-generated `_baked` module, and raises `ConfigError` with instructions when it finds neither. `gslist.py` fetches and parses the list and owns the region model. `stats.py` turns a list of ping times into min/max/avg/stddev.

Choices worth knowing before you touch this code:

- The country-to-region table maps far more country codes than the server list currently uses. That's deliberate future-proofing: when a new server appears in, say, Poland or Thailand, it lands in the right region with no code change. Russia (and any transcontinental country) maps to two regions at once, so filtering by either continent picks it up.
- A server whose country code isn't in the table is not an error. It forms an unsorted bucket: it still gets pinged like any other server, continent filters just don't match it. The CLI will print a warning listing these codes. `unknown_country_codes()` is the helper for that.
- `gb` and `uk` are the same country as far as filtering goes. Users can type either regardless of what the data file uses.
- Filter validation accepts a token if it's a country code observed in the fetched data, a code in the built-in table, or a region keyword. The old tool rejected codes with no current servers; v2 accepts them and reports zero matches instead, which is friendlier when the list changes.
- Region keywords are lowercase continent names without underscores (`northamerica`, `europe`, ...), matching the old tool's vocabulary. Matching is case-insensitive now; it wasn't before.
- StdDev uses the true mean (`statistics.pstdev`). The old tool centered its stddev on the already-rounded average, a small quirk not worth reproducing; differences show up in the hundredths, well below what the report prints.
- Tests never touch the network (the fetch test reads through a `file://` URL) and never use real server IPs. The fixture uses the RFC 5737 documentation ranges, which exist for exactly this purpose.
- The leak guard test does two things unconditionally: verifies `.env` and `src/core/_baked.py` are actually gitignored. And when a real URL is available (from the `GS_LIST_URL` environment variable or a local `.env`), it scans every git-trackable file for that string and fails loudly. With no URL configured it skips, so fresh clones and contributor machines don't produce false failures. In CI the environment variable will come from the GitHub secret, making the scan real where it matters.

## Phase 2 notes: the pinger

`pinger.py` wraps icmplib and makes one call the code can't explain on its own: which ICMP mechanism to use. Machines differ. Windows and macOS allow unprivileged ICMP sockets, plain Linux doesn't (the kernel gates them behind the `net.ipv4.ping_group_range` sysctl), and a container often has neither that sysctl set nor a `ping` binary with file capabilities. So the pinger tries, in order: unprivileged ICMP, privileged ICMP (works as root), then the system `ping` binary, which most distros ship with the capability already attached. The first mechanism that answers wins and is cached for the rest of the run.

The probe pings `127.0.0.1`, so detection never touches the network. One quirk we hit while testing: some iputils builds suppress the per-reply `time=` field, and even the whole summary line, when the payload is tiny. That made the probe fail on machines where real pings worked. Two fixes landed: the probe uses the same payload size as real pings, and the output parser learned the Linux/macOS `rtt min/avg/max/mdev` summary line as a second pattern.

What keeps parity with the old tool:

- Two-second timeout, 32-byte payload, one ping per attempt, attempts run one after another. Same numbers as before.
- A failed attempt is recorded as `None`, not an error. Stats skip `None` values, which reproduces how the old tool's report behaved.
- If nothing works at all, the tool raises `PingError` with the Linux sysctl fix in the message. Users who hit that need an OS config change, not a bug report.

The system-ping fallback is the only mode that parses CLI output, so it parses tolerantly: strict English `time=` first, then the summary line, then a loose `[=<] N ms` pattern that handles localized output such as French `temps=23,5 ms`. The loose pattern is safe for one reason: we ping with a count of 1, so every "N ms" value in the output describes the same packet.

`ping_server()` takes an optional `on_attempt` callback that fires after each try with the attempt number and result. The CLI driver doesn't use it (the old tool printed nothing between "Pinging:" lines either); the future Textual UI will.

Tests keep the no-network rule from phase 1. They fake the icmplib and subprocess layers and stick to the RFC 5737 ranges; `resolve_mode()` is exercised but only ever pings loopback.

## Phase 3 notes: the report and the driver

`output.py` is pure string work: `collect()` pairs a server with its raw ping list and folds in the stats, `render_report()` turns a list of results into the report text. Nothing in the module prints, so tests compare strings instead of scraping stdout. The driver in `__main__.py` owns every `input()` and `print()`.

The prompt order looks odd but is faithful to the old tool: it asks for tries before fetching the server list. Kept as is.

Where v2 deliberately parts ways with the old output:

- The old tool threw away a server's whole measurement if a single ping failed. v2 still keeps failures out of the stats, but computes from the replies that did land, and only marks a server SKIPPED when nothing came back at all. Partial loss shows up as "(n/m replies lost)" on the row.
- Numbers print with one decimal instead of the old rounded integers.
- Rows with StdDev over 10 get an explicit "unstable" tag. The old tool only explained that rule in the header text, which is kept.
- Filter input accepts commas as separators, not just spaces.
- The report prints which ping mechanism was detected. When someone pastes output into a bug report, that line answers the first question anyone asks.

Kept from the old tool on purpose: the banner, the "Press ENTER to exit." pause, and the overall wording of the flow. The pause exists because a double-clicked Windows exe closes its console the instant the process exits; without it users would never see the report. The version line comes from installed package metadata and falls back to "dev" when the project isn't installed.

Scripted runs: EOF at any prompt aborts with exit code 130 ("Aborted."), but the final pause treats EOF as "carry on", so piping input into the tool exits cleanly instead of hanging.

Tests stay offline: report rendering is checked against fake servers on RFC 5737 addresses, and the two input helpers (`_parse_tries`, `_parse_tokens`) are tested directly.

## Phase 4 notes: building and releasing

`scripts/build.py` is the one command behind a release binary: it bakes the URL and runs PyInstaller. Two choices in it that the code doesn't spell out:

- The URL for baking comes from the environment or `.env`, never from a previous `_baked.py`. Reading back the old baked module would let a stale URL sneak into a fresh build.
- After building, the script smoke-tests the binary by running it with stdin closed. The driver then aborts at the first prompt with exit code 130 after printing the banner, and the script checks for exactly that. It proves the bundle starts and the entry point is wired up, without pinging anyone. `--no-smoke` skips it.

PyInstaller's work and spec files live inside `build/` (gitignored) so nothing extra lands in the repo root. A local build produced a 21 MiB one-file binary on Linux; the other platforms ride on the same script.

`.github/workflows/release.yml` triggers on `v*` tags only. The maintainer must add the `GS_LIST_URL` secret in the repo settings before the first tag push; if it's missing, the workflow stops before building. That explicit check exists because the leak guard test would otherwise quietly skip instead of scan. Each matrix leg (Windows, Linux, macOS) runs the full test suite, so the leak guard scan is a real one on CI, then builds and uploads the binary named `mxl-sigma-ultt-<tag>-<platform>`. A second job collects all three and attaches them to the GitHub release. That split means a broken platform can't produce a half release: the release job only runs when every leg passed.

Actions are pinned to exact versions instead of floating major tags. setup-uv stopped publishing major tags over supply-chain concerns; applying the same habit to the rest costs nothing.

## Phase 5 notes: shipping

The README was rewritten for v2: cross-platform instead of Windows-only, terminal report instead of output.txt, plus the things a new user can't guess — the SmartScreen and Gatekeeper warnings for unsigned binaries, the Linux ping-socket sysctl, and the GS 6 / tries=1 quirks carried over from the old README.

One incident worth keeping on record: the first README draft quoted the real server list URL in the build-from-source section, and the phase 1 leak guard test caught it before any commit. The README now explains how to get the URL without printing it. That test earning its first catch is the best argument for keeping it.

The license situation is stated in the README: this repo is MIT, icmplib is LGPL-3.0 and stays a separately linked library. Since the source repo is public and icmplib is unmodified, that satisfies the license without extra ceremony.

`MXLLagtest.py` is deleted and the ruff exclude for it (a Python 2 file ruff couldn't parse) went with it.

Releasing, end to end, for the maintainer:

1. Make sure the `GS_LIST_URL` secret exists in the repo settings (Actions → Secrets and variables).
2. Commit, then tag `v2.0.0` and push the tag.
3. GitHub Actions builds the three binaries and attaches them to the release; check the run is green.
4. Spot-check each binary on its own OS. First runs will trip SmartScreen (Windows) or Gatekeeper (macOS); the README tells users what to click through.

## The plan and where it stands

Rewrite phases, in order. Each appends to this file when it finishes.

0. Scaffolding: uv project, lint/test config, entry point. **done**
1. Data layer: fetch, parse, region filtering, with tests. **done**
2. Pinger: sequential pings, failure handling, privilege fallback. **done**
3. Terminal output and CLI driver. At this point v2 matches the old tool feature for feature. **done**
4. Build script and CI: release binaries for Windows, Linux, macOS via GitHub Actions. **done**
5. Ship: README rewrite, delete `MXLLagtest.py`, tag v2.0.0. **done**
