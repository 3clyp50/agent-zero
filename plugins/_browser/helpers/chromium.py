from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from plugins._browser.helpers.playwright import get_playwright_binary


CHROMIUM_BINARY_ENV = "A0_BROWSER_CHROMIUM_BINARY"
SYSTEM_CHROMIUM_CANDIDATES = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "chrome",
)


def get_chromium_binary() -> Path | None:
    described = describe_chromium_binary()
    path = described.get("binary_path")
    return Path(path) if path else None


def ensure_chromium_binary() -> Path:
    binary = get_chromium_binary()
    if binary:
        return binary
    raise RuntimeError(
        "Chromium was not found for the Browser CDP runtime. "
        f"Set {CHROMIUM_BINARY_ENV} to a Chromium/Chrome executable, install a system "
        "Chromium package, or make sure the Docker image prepared the cached "
        "Chromium headless shell under /a0/tmp/playwright."
    )


def describe_chromium_binary() -> dict[str, Any]:
    env_binary = _env_binary()
    if env_binary:
        return _description(env_binary, source="env", install_required=False)

    cached_binary = get_playwright_binary()
    if cached_binary:
        return _description(cached_binary, source="playwright_cache", install_required=False)

    system_binary = _system_binary()
    if system_binary:
        return _description(system_binary, source="system", install_required=False)

    return {
        "binary_found": False,
        "binary_path": "",
        "source": "",
        "install_required": True,
        "env": CHROMIUM_BINARY_ENV,
        "system_candidates": list(SYSTEM_CHROMIUM_CANDIDATES),
    }


def _description(path: Path, *, source: str, install_required: bool) -> dict[str, Any]:
    return {
        "binary_found": True,
        "binary_path": str(path),
        "source": source,
        "install_required": install_required,
        "env": CHROMIUM_BINARY_ENV,
        "system_candidates": list(SYSTEM_CHROMIUM_CANDIDATES),
    }


def _env_binary() -> Path | None:
    raw_path = os.environ.get(CHROMIUM_BINARY_ENV, "").strip()
    if not raw_path:
        return None
    path = Path(raw_path).expanduser()
    return path if path.is_file() and os.access(path, os.X_OK) else None


def _system_binary() -> Path | None:
    for candidate in SYSTEM_CHROMIUM_CANDIDATES:
        found = shutil.which(candidate)
        if found:
            return Path(found)
    return None
