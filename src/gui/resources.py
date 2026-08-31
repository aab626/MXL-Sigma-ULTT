"""Locate bundled assets in dev and frozen (PyInstaller) environments."""

import sys
from pathlib import Path


def asset_path(name: str) -> Path | None:
    """Return an asset's path, or None when missing (callers fail silently)."""
    bundled = getattr(sys, "_MEIPASS", None)
    base = Path(bundled) / "gui" / "assets" if bundled else Path(__file__).parent / "assets"
    path = base / name
    return path if path.is_file() else None
