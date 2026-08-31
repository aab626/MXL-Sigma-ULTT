import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]


def _git_check_ignore(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", path],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    return result.returncode == 0


def test_env_file_is_gitignored():
    assert _git_check_ignore(".env")


def test_baked_module_is_gitignored():
    assert _git_check_ignore("src/core/_baked.py")


def _find_secret() -> str:
    secret = os.environ.get("GS_LIST_URL", "").strip()
    if secret:
        return secret
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("GS_LIST_URL="):
            return line.split("=", 1)[1].strip()
    return ""


def test_secret_url_absent_from_trackable_files():
    secret = _find_secret()
    if not secret:
        pytest.skip("no GS_LIST_URL configured, nothing to guard")

    tracked = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    for name in tracked:
        path = REPO_ROOT / name
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        assert secret not in content, f"leaked secret found in {name}"
