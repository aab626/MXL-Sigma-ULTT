# Development notes

This file is the project's memory. It explains how to work on MXL-Sigma-ULTT without needing the chat that planned the rewrite. Anything the code already says clearly stays out of here; this is for instructions, context, and decisions that would otherwise get lost.

## What this project is

A small CLI tool for the Median XL Sigma community. It downloads the game server list, lets the user filter servers by country code or continent keyword, pings each server, and prints a latency report (min, max, avg, stddev, plus a top five). v2 is a rewrite of the original Python 2 `MXLLagtest.py`, which still sits in the repo root as a behavioral reference and gets deleted once v2 ships. Don't try to run or lint that file; it's Python 2 and ruff is configured to ignore it.

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

## The plan and where it stands

Rewrite phases, in order. Each appends to this file when it finishes.

0. Scaffolding: uv project, lint/test config, entry point. **done**
1. Data layer: fetch, parse, region filtering, with tests.
2. Pinger: sequential pings, failure handling, privilege fallback.
3. Terminal output and CLI driver. At this point v2 matches the old tool feature for feature.
4. Build script and CI: release binaries for Windows, Linux, macOS via GitHub Actions.
5. Ship: README rewrite, delete `MXLLagtest.py`, tag v2.0.0.
