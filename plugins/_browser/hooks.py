from __future__ import annotations

import importlib
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

from helpers import files, plugins, yaml as yaml_helper
from plugins._browser.helpers.config import (
    PLUGIN_NAME,
    browser_runtime_config,
    normalize_browser_config,
)
from plugins._browser.helpers.playwright import (
    find_full_chromium_payloads,
    find_playwright_binary,
    get_playwright_cache_dir,
    get_retired_playwright_cache_dirs,
)


PYTHON_RUNTIME_DEPENDENCIES = (
    ("aiohttp", "aiohttp>=3.10.0"),
)


def _load_saved_browser_config(project_name: str = "", agent_profile: str = "") -> dict:
    entries = plugins.find_plugin_assets(
        plugins.CONFIG_FILE_NAME,
        plugin_name=PLUGIN_NAME,
        project_name=project_name,
        agent_profile=agent_profile,
        only_first=True,
    )
    path = entries[0].get("path", "") if entries else ""
    if path and files.exists(path):
        return files.read_file_json(path) or {}

    plugin_dir = plugins.find_plugin_dir(PLUGIN_NAME)
    default_path = (
        files.get_abs_path(plugin_dir, plugins.CONFIG_DEFAULT_FILE_NAME)
        if plugin_dir
        else ""
    )
    if default_path and files.exists(default_path):
        return yaml_helper.loads(files.read_file(default_path)) or {}

    return {}


def get_plugin_config(default=None, **kwargs):
    return normalize_browser_config(default)


def save_plugin_config(settings=None, project_name="", agent_profile="", **kwargs):
    normalized = normalize_browser_config(settings)
    current = normalize_browser_config(
        _load_saved_browser_config(project_name=project_name, agent_profile=agent_profile)
    )
    if browser_runtime_config(normalized) != browser_runtime_config(current):
        close_all_runtimes_sync()
    return normalized


def close_all_runtimes_sync() -> None:
    from plugins._browser.helpers.runtime import close_all_runtimes_sync as close_all

    close_all()


def ensure_python_runtime_dependencies() -> dict:
    installed: list[str] = []
    errors: list[str] = []
    for import_name, requirement in PYTHON_RUNTIME_DEPENDENCIES:
        if importlib.util.find_spec(import_name) is not None:
            continue
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", requirement],
            check=False,
            text=True,
            capture_output=True,
            timeout=300,
        )
        if result.returncode == 0:
            importlib.invalidate_caches()
            installed.append(requirement)
            continue
        output = (result.stderr or result.stdout or f"pip install {requirement} failed").strip()
        errors.append(output)

    return {
        "ok": not errors,
        "installed": installed,
        "errors": errors,
    }


def cleanup_playwright_cache() -> dict:
    primary = Path(get_playwright_cache_dir())
    retired_dirs = [
        path for path in get_retired_playwright_cache_dirs() if path.resolve() != primary.resolve()
    ]
    result = {"primary": str(primary), "migrated": "", "removed": [], "errors": []}

    if find_playwright_binary(primary):
        _remove_full_chromium_payloads([primary, *retired_dirs], result)
        _remove_cache_dirs(retired_dirs, result)
        return result

    source = _best_playwright_cache(retired_dirs)
    if not source:
        return result

    backup = _next_backup_path(primary) if primary.exists() else None
    try:
        if backup:
            primary.rename(backup)
        primary.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(primary))
        result["migrated"] = str(source)
    except Exception as exc:
        if backup and backup.exists() and not primary.exists():
            backup.rename(primary)
        result["errors"].append(f"Failed to migrate {source} to {primary}: {exc}")
        return result

    if not find_playwright_binary(primary):
        result["errors"].append(f"Migrated Playwright cache is not valid: {primary}")
        if backup:
            result["errors"].append(f"Previous primary Playwright cache retained at {backup}")
        return result

    if backup:
        _remove_cache_dirs([backup], result)
    _remove_full_chromium_payloads([primary, *retired_dirs], result)
    _remove_cache_dirs(retired_dirs, result)
    return result


def _best_playwright_cache(candidates: list[Path]) -> Path | None:
    valid = [path for path in candidates if path.is_dir() and find_playwright_binary(path)]
    if not valid:
        return None

    def modified_at(path: Path) -> float:
        binary = find_playwright_binary(path)
        try:
            return binary.stat().st_mtime if binary else path.stat().st_mtime
        except OSError:
            return 0

    return max(valid, key=modified_at)


def _next_backup_path(path: Path) -> Path:
    backup = path.with_name(f"{path.name}.migration-backup")
    counter = 2
    while backup.exists():
        backup = path.with_name(f"{path.name}.migration-backup-{counter}")
        counter += 1
    return backup


def _remove_cache_dirs(paths: list[Path], result: dict) -> None:
    for path in paths:
        if not path.exists():
            continue
        try:
            shutil.rmtree(path)
            result["removed"].append(str(path))
        except Exception as exc:
            result["errors"].append(f"Failed to remove Playwright cache {path}: {exc}")


def _remove_full_chromium_payloads(paths: list[Path], result: dict) -> None:
    for cache_dir in paths:
        if not cache_dir.exists():
            continue
        for payload in find_full_chromium_payloads(cache_dir):
            try:
                shutil.rmtree(payload)
                result["removed"].append(str(payload))
            except Exception as exc:
                result["errors"].append(f"Failed to remove full Chromium payload {payload}: {exc}")
