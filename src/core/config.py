import os

from dotenv import load_dotenv


class ConfigError(Exception):
    pass


def get_gs_list_url() -> str:
    load_dotenv()
    url = os.environ.get("GS_LIST_URL", "").strip()
    if not url:
        url = _baked_url()
    if not url:
        raise ConfigError(
            "GS_LIST_URL is not set. Copy .env.example to .env, set it, and run "
            "from the repo root. Release binaries have the URL baked in at build time."
        )
    return url


def _baked_url() -> str:
    try:
        from core import _baked
    except ImportError:
        return ""
    return getattr(_baked, "GS_LIST_URL", "").strip()
