"""Build a one-file release binary.

Bakes the server list URL into ``src/core/_baked.py`` (gitignored), then
runs PyInstaller. Run with ``uv run python scripts/build.py``. The URL
comes from the ``GS_LIST_URL`` environment variable or a ``.env`` file in
the repo root. The baked module is never read back here on purpose: a
stale ``_baked.py`` from an earlier build must not silently provide the
URL for a new one.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NAME = "mxl-sigma-ultt"
ENTRY = REPO_ROOT / "src" / "core" / "__main__.py"
BAKED = REPO_ROOT / "src" / "core" / "_baked.py"
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
            str(ENTRY),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    return binary


def smoke(binary: Path) -> None:
    """Run the binary with stdin closed.

    The driver hits EOF at the first prompt and exits with code 130 after
    printing the banner, which proves the bundle starts and the entry
    point is wired up.
    """
    result = subprocess.run(
        [str(binary)],
        input="",
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 130 or "MEDIAN XL SIGMA" not in result.stdout:
        raise SystemExit(
            f"Smoke test failed: exit {result.returncode}.\nstdout:\n{result.stdout}"
        )
    print("Smoke test passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a one-file release binary.")
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
