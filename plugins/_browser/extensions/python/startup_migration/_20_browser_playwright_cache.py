from __future__ import annotations

import threading
from typing import Any

from helpers.extension import Extension
from helpers.print_style import PrintStyle
from plugins._browser import hooks


_startup_migration_thread: threading.Thread | None = None


class BrowserPlaywrightCacheMigration(Extension):
    def execute(self, **kwargs):
        _start_background_runtime_preparation()


def _start_background_runtime_preparation() -> threading.Thread:
    global _startup_migration_thread

    if _startup_migration_thread and _startup_migration_thread.is_alive():
        return _startup_migration_thread

    _startup_migration_thread = threading.Thread(
        target=_prepare_runtime_safely,
        name="a0-browser-runtime-preparation",
        daemon=True,
    )
    _startup_migration_thread.start()
    return _startup_migration_thread


def _prepare_runtime_safely() -> None:
    try:
        _log_python_dependency_result(hooks.ensure_python_runtime_dependencies())
        _log_cache_migration_result(hooks.cleanup_playwright_cache())
    except Exception as exc:
        PrintStyle.warning("Browser runtime preparation failed:", exc)


def _log_python_dependency_result(result: dict[str, Any]) -> None:
    if result.get("errors"):
        PrintStyle.warning("Browser Python dependency preparation reported errors:", result["errors"])
    elif result.get("installed"):
        PrintStyle.info("Browser Python dependencies prepared:", result)


def _log_cache_migration_result(result: dict[str, Any]) -> None:
    if result.get("errors"):
        PrintStyle.warning("Browser Playwright cache migration reported errors:", result["errors"])
    elif result.get("migrated") or result.get("removed"):
        PrintStyle.info("Browser Playwright cache prepared:", result)
