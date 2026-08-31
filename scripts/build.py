"""Build the windowed one-file release binary.

Bakes the server list URL into ``src/core/_baked.py`` (gitignored), then
runs PyInstaller against the Qt GUI. Run with ``uv run python scripts/build.py``.
The URL comes from the ``GS_LIST_URL`` environment variable or a ``.env``
file in the repo root. The baked module is never read back here on purpose:
a stale ``_baked.py`` from an earlier build must not silently provide the
URL for a new one.

The GUI ships as a windowed binary (--windowed): no console window opens on
Windows. Its smoke test therefore cannot rely on stdout; the ``--smoke``
flag builds the real window offscreen and exits 0, and that exit code is
the whole contract.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NAME = "mxl-sigma-ultt"
ENTRY = REPO_ROOT / "src" / "gui" / "__main__.py"
BAKED = REPO_ROOT / "src" / "core" / "_baked.py"
ASSETS = REPO_ROOT / "src" / "gui" / "assets"
DIST = REPO_ROOT / "dist"


def resolve_url() -> str:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    url = os.environ.get("GS_LIST_URL", "").strip()
    if not url:
        raise SystemExit(
            "GS_LIST_URL is not set. Export it or put it in a .env file in "
            "the repo root before building."
        )
    return url


def bake(url: str) -> None:
    BAKED.write_text(f"GS_LIST_URL = {url!r}\n", encoding="utf-8")
    print(f"Baked server list URL into {BAKED.relative_to(REPO_ROOT)}")


def build() -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    binary = DIST / (NAME + suffix)
    binary.unlink(missing_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--windowed",
            "--name",
            NAME,
            "--distpath",
            str(DIST),
            "--workpath",
            str(REPO_ROOT / "build"),
            "--specpath",
            str(REPO_ROOT / "build"),
            "--paths",
            str(REPO_ROOT / "src"),
            "--add-data",
            f"{ASSETS}{os.pathsep}gui/assets",
            str(ENTRY),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    return binary


def smoke(binary: Path) -> None:
    """Run the binary with ``--smoke`` on the offscreen Qt platform.

    This constructs the real MainWindow (fonts, stylesheet, widgets) inside
    the frozen bundle and exits 0. Windowed binaries have no stdout on
    Windows, so the return code is the only assertion.
    """
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [str(binary), "--smoke"],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"Smoke test failed: exit {result.returncode}.\nstdout:\n{result.stdout}"
            f"\nstderr:\n{result.stderr}"
        )
    print("Smoke test passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the one-file GUI release binary.")
    parser.add_argument(
        "--no-smoke", action="store_true", help="skip the post-build smoke test"
    )
    args = parser.parse_args()

    bake(resolve_url())
    binary = build()
    if not args.no_smoke:
        smoke(binary)
    size = binary.stat().st_size / (1024 * 1024)
    print(f"Built {binary} ({size:.1f} MiB)")


if __name__ == "__main__":
    main()
