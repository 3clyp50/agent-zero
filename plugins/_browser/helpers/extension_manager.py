from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from helpers import files, plugins
from plugins._browser.helpers.config import PLUGIN_NAME, get_browser_config
from plugins._browser.helpers.runtime import close_all_runtimes_sync


EXTENSIONS_ROOT_DIR = ("usr", "_browser", "extensions")
EXTENSION_ID_RE = re.compile(r"^[a-p]{32}$")
WEB_STORE_ID_RE = re.compile(r"(?<![a-p])([a-p]{32})(?![a-p])")
CHROME_VERSION_RE = re.compile(r"(\d+(?:\.\d+){0,3})")
CHROME_I18N_MESSAGE_RE = re.compile(r"__MSG_([A-Za-z0-9_@.-]+)__")
DEFAULT_CHROME_PRODVERSION = "140.0.0.0"
EXTENSION_ID_ALPHABET = "abcdefghijklmnop"
CHROME_VERSION_COMMANDS = (
    ("google-chrome", "--version"),
    ("chromium", "--version"),
    ("chromium-browser", "--version"),
)
WEB_STORE_DOWNLOAD_URL = (
    "https://clients2.google.com/service/update2/crx"
    "?response=redirect"
    "&prod=chromecrx"
    "&prodversion={prodversion}"
    "&acceptformat=crx2,crx3"
    "&x=id%3D{extension_id}%26installsource%3Dondemand%26uc"
)


def get_extensions_root() -> Path:
    return Path(files.get_abs_path(*EXTENSIONS_ROOT_DIR))


def parse_chrome_web_store_extension_id(value: str) -> str:
    source = str(value or "").strip()
    if EXTENSION_ID_RE.fullmatch(source):
        return source

    match = WEB_STORE_ID_RE.search(source)
    if match:
        return match.group(1)

    raise ValueError("Enter a Chrome Web Store URL or a 32-character extension id.")


def list_browser_extensions() -> list[dict[str, Any]]:
    config = get_browser_config()
    enabled_paths = {str(Path(path).expanduser()) for path in config["extension_paths"]}
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    root = get_extensions_root()
    if root.exists():
        for manifest_path in sorted(root.glob("**/manifest.json")):
            if any(part.startswith(".") for part in manifest_path.relative_to(root).parts):
                continue
            entry = _extension_entry(manifest_path.parent, enabled_paths)
            seen.add(entry["path"])
            entries.append(entry)

    for configured_path in config["extension_paths"]:
        extension_dir = Path(configured_path).expanduser()
        extension_path = str(extension_dir)
        if extension_path in seen or not (extension_dir / "manifest.json").is_file():
            continue
        entries.append(_extension_entry(extension_dir, enabled_paths))
        seen.add(extension_path)

    return entries


def install_chrome_web_store_extension(source: str) -> dict[str, Any]:
    extension_id = parse_chrome_web_store_extension_id(source)
    target = get_extensions_root() / "chrome-web-store" / extension_id

    with tempfile.TemporaryDirectory(prefix="browser-extension-control-") as tmp:
        archive_path = Path(tmp) / f"{extension_id}.crx"
        _download_crx(extension_id, archive_path)
        payload_path = Path(tmp) / f"{extension_id}.zip"
        payload_path.write_bytes(_crx_zip_payload(archive_path.read_bytes()))
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(payload_path) as archive:
                manifest = json.loads(archive.read("manifest.json"))
        except KeyError as exc:
            raise ValueError("Downloaded extension did not contain a manifest.json file.") from exc
        except (json.JSONDecodeError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
            raise ValueError("Downloaded extension contained an invalid manifest.json file.") from exc
        if not isinstance(manifest, dict):
            raise ValueError("Downloaded extension contained an invalid manifest.json file.")

        current_manifest = _read_manifest(target)
        if not (
            target.is_dir()
            and manifest.get("version")
            and manifest.get("version") == current_manifest.get("version")
        ):
            with tempfile.TemporaryDirectory(
                prefix=f".{extension_id}-install-",
                dir=target.parent,
            ) as extracted:
                extracted_path = Path(extracted)
                _safe_extract_zip(payload_path, extracted_path)
                config = get_browser_config()
                if target.exists() and str(target) in config["extension_paths"]:
                    close_all_runtimes_sync()
                _replace_extension_dir(extracted_path, target)

    config = _enable_extension_path(target)
    manifest = _read_manifest(target)
    return {
        "ok": True,
        "id": extension_id,
        "name": _manifest_label(target, manifest, "name") or extension_id,
        "version": manifest.get("version") or "",
        "path": str(target),
        "extension_paths": config["extension_paths"],
    }


def _replace_extension_dir(source: Path, target: Path) -> None:
    if not target.exists():
        source.rename(target)
        return

    with tempfile.TemporaryDirectory(
        prefix=f".{target.name}-previous-",
        dir=target.parent,
    ) as backup_dir:
        backup = Path(backup_dir) / target.name
        target.rename(backup)
        try:
            source.rename(target)
        except BaseException:
            backup.rename(target)
            raise


def set_browser_extension_enabled(extension_path: str, enabled: bool) -> dict[str, Any]:
    raw_path = str(extension_path or "").strip()
    if not raw_path:
        raise ValueError("Choose an extension first.")

    path = str(Path(raw_path).expanduser())
    directory = Path(path)
    if enabled and not (directory / "manifest.json").is_file():
        raise ValueError("Extension folder must contain a manifest.json file.")

    config = get_browser_config()
    paths = list(config["extension_paths"])
    if enabled:
        if path not in paths:
            paths.append(path)
    else:
        paths = [item for item in paths if str(Path(item).expanduser()) != path]

    config["extension_paths"] = paths
    plugins.save_plugin_config(PLUGIN_NAME, "", "", config)
    return config


def uninstall_browser_extension(extension_path: str) -> dict[str, Any]:
    raw_path = str(extension_path or "").strip()
    if not raw_path:
        raise ValueError("Choose an extension first.")

    root = get_extensions_root().resolve()
    extension_dir = Path(raw_path).expanduser().resolve()
    if extension_dir == root or not extension_dir.is_relative_to(root):
        raise ValueError("Only Browser-managed extension folders can be deleted.")
    if not extension_dir.is_dir():
        raise ValueError("Extension folder was not found.")

    manifest = _read_manifest(extension_dir)
    name = (
        _manifest_label(extension_dir, manifest, "name")
        or _manifest_label(extension_dir, manifest, "short_name")
        or extension_dir.name
    )
    config = get_browser_config()
    config["extension_paths"] = [
        path
        for path in config["extension_paths"]
        if Path(path).expanduser().resolve() != extension_dir
    ]

    try:
        shutil.rmtree(extension_dir)
    except OSError as exc:
        raise ValueError(f"Could not delete extension folder: {exc}") from exc

    plugins.save_plugin_config(PLUGIN_NAME, "", "", config)
    return {
        "ok": True,
        "name": name,
        "path": str(extension_dir),
        "extension_paths": config["extension_paths"],
    }


def _download_crx(extension_id: str, archive_path: Path) -> None:
    prodversion = _detect_chrome_prodversion()
    url = _build_web_store_download_url(extension_id, prodversion=prodversion)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                f"(KHTML, like Gecko) Chrome/{prodversion} Safari/537.36"
            )
        },
    )
    try:
        response = urllib.request.urlopen(request, timeout=120)
    except urllib.error.HTTPError as exc:
        raise ValueError(
            f"Chrome Web Store download failed with HTTP {exc.code} for Chrome {prodversion}."
        ) from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise ValueError(f"Chrome Web Store download failed: {reason}.") from exc

    with response:
        status = response.getcode()
        data = response.read()
    if not data:
        raise ValueError(
            "Chrome Web Store did not return an extension package "
            f"(HTTP {status}, Chrome {prodversion})."
        )
    archive_path.write_bytes(data)


def _build_web_store_download_url(extension_id: str, *, prodversion: str | None = None) -> str:
    return WEB_STORE_DOWNLOAD_URL.format(
        extension_id=extension_id,
        prodversion=_normalize_chrome_prodversion(prodversion or "") or DEFAULT_CHROME_PRODVERSION,
    )


def _detect_chrome_prodversion() -> str:
    env_version = _normalize_chrome_prodversion(os.environ.get("A0_BROWSER_EXTENSION_PRODVERSION", ""))
    if env_version:
        return env_version

    for command in CHROME_VERSION_COMMANDS:
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue

        version = _normalize_chrome_prodversion(
            " ".join(part for part in (completed.stdout, completed.stderr) if part)
        )
        if version:
            return version

    return DEFAULT_CHROME_PRODVERSION


def _normalize_chrome_prodversion(value: str) -> str:
    match = CHROME_VERSION_RE.search(str(value or ""))
    if not match:
        return ""
    parts = match.group(1).split(".")
    return ".".join((parts + ["0", "0", "0", "0"])[:4])


def _crx_zip_payload(data: bytes) -> bytes:
    if data.startswith(b"PK"):
        return data
    if data[:4] != b"Cr24":
        raise ValueError("Downloaded package is not a CRX or ZIP archive.")

    version = int.from_bytes(data[4:8], "little")
    if version == 2:
        public_key_len = int.from_bytes(data[8:12], "little")
        signature_len = int.from_bytes(data[12:16], "little")
        offset = 16 + public_key_len + signature_len
    elif version == 3:
        header_len = int.from_bytes(data[8:12], "little")
        offset = 12 + header_len
    else:
        raise ValueError(f"Unsupported CRX version: {version}.")

    payload = data[offset:]
    if not payload.startswith(b"PK"):
        raise ValueError("CRX payload did not contain a ZIP archive.")
    return payload


def _safe_extract_zip(archive_path: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    root = target_dir.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            destination = (target_dir / member.filename).resolve()
            if not destination.is_relative_to(root):
                raise ValueError("Extension archive contains an unsafe path.")
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)


def _enable_extension_path(extension_path: Path) -> dict[str, Any]:
    config = get_browser_config()
    path = str(extension_path)
    paths = list(config["extension_paths"])
    if path not in paths:
        paths.append(path)
    config["extension_paths"] = paths
    plugins.save_plugin_config(PLUGIN_NAME, "", "", config)
    return config


def _extension_entry(extension_dir: Path, enabled_paths: set[str]) -> dict[str, Any]:
    manifest = _read_manifest(extension_dir)
    extension_path = str(extension_dir)
    can_delete = _is_managed_extension_dir(extension_dir)
    extension_id = _extension_runtime_id(extension_dir, manifest)
    source_id = _extension_source_id(extension_dir)
    ui = _extension_ui(extension_id, manifest)
    name = (
        _manifest_label(extension_dir, manifest, "name")
        or _manifest_label(extension_dir, manifest, "short_name")
        or extension_dir.name
    )
    return {
        "id": extension_id,
        "source_id": source_id,
        "name": name,
        "raw_name": manifest.get("name") or "",
        "description": _manifest_label(extension_dir, manifest, "description"),
        "version": manifest.get("version") or "",
        "path": extension_path,
        "enabled": extension_path in enabled_paths,
        "managed": can_delete,
        "can_delete": can_delete,
        "has_ui": bool(ui["open_url"]),
        "open_url": ui["open_url"],
        "open_label": ui["open_label"],
        "ui": ui,
    }


def _is_managed_extension_dir(extension_dir: Path) -> bool:
    try:
        root = get_extensions_root().resolve()
        path = extension_dir.expanduser().resolve()
    except OSError:
        return False
    return path != root and path.is_relative_to(root)


def _read_manifest(extension_path: Path) -> dict[str, Any]:
    manifest_path = extension_path / "manifest.json"
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _extension_runtime_id(extension_dir: Path, manifest: dict[str, Any]) -> str:
    key_id = _extension_id_from_manifest_key(str(manifest.get("key") or ""))
    if key_id:
        return key_id
    return _extension_id_from_path(extension_dir)


def _extension_source_id(extension_dir: Path) -> str:
    name = extension_dir.name
    if not EXTENSION_ID_RE.fullmatch(name):
        return ""
    try:
        if extension_dir.parent.name == "chrome-web-store":
            return name
    except OSError:
        return ""
    return ""


def _extension_id_from_manifest_key(key: str) -> str:
    raw_key = str(key or "").strip()
    if not raw_key:
        return ""
    try:
        padding = "=" * (-len(raw_key) % 4)
        public_key = base64.b64decode(raw_key + padding, validate=True)
    except Exception:
        return ""
    return _extension_id_from_hash_input(public_key)


def _extension_id_from_path(extension_dir: Path) -> str:
    return _extension_id_from_hash_input(str(extension_dir).encode("utf-8"))


def _extension_id_from_hash_input(value: bytes) -> str:
    digest = hashlib.sha256(value).hexdigest()[:32]
    return "".join(EXTENSION_ID_ALPHABET[int(char, 16)] for char in digest)


def _extension_ui(extension_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    targets = _extension_ui_targets(extension_id, manifest)
    primary = targets[0] if targets else {}
    return {
        "open_url": primary.get("url", ""),
        "open_label": primary.get("label", ""),
        "targets": targets,
    }


def _extension_ui_targets(extension_id: str, manifest: dict[str, Any]) -> list[dict[str, str]]:
    candidates: list[tuple[str, str, Any]] = [
        ("options", "Options", _manifest_nested_value(manifest, "options_ui", "page")),
        ("options", "Options", manifest.get("options_page")),
        ("popup", "Popup", _manifest_nested_value(manifest, "action", "default_popup")),
        ("popup", "Popup", _manifest_nested_value(manifest, "browser_action", "default_popup")),
        ("popup", "Popup", _manifest_nested_value(manifest, "page_action", "default_popup")),
        ("side_panel", "Side panel", _manifest_nested_value(manifest, "side_panel", "default_path")),
        ("devtools", "DevTools", manifest.get("devtools_page")),
    ]

    chrome_url_overrides = manifest.get("chrome_url_overrides")
    if isinstance(chrome_url_overrides, dict):
        candidates.extend(
            (
                (f"chrome_url_override_{name}", _extension_override_label(name), page)
                for name, page in chrome_url_overrides.items()
            )
        )

    targets: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for kind, label, page in candidates:
        url = _extension_page_url(extension_id, page)
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        targets.append(
            {
                "kind": kind,
                "label": label,
                "page": str(page or "").strip(),
                "url": url,
            }
        )
    return targets


def _manifest_nested_value(manifest: dict[str, Any], key: str, nested_key: str) -> Any:
    value = manifest.get(key)
    if not isinstance(value, dict):
        return ""
    return value.get(nested_key)


def _extension_override_label(name: str) -> str:
    normalized = str(name or "").replace("_", " ").strip()
    return normalized[:1].upper() + normalized[1:] if normalized else "Extension page"


def _extension_page_url(extension_id: str, page: Any) -> str:
    page_path = str(page or "").strip()
    if not extension_id or not page_path:
        return ""
    if re.match(r"^[a-z][a-z0-9+.-]*:", page_path, flags=re.IGNORECASE):
        return ""
    page_path = page_path.lstrip("/")
    if not page_path:
        return ""
    return f"chrome-extension://{extension_id}/{page_path}"


def _manifest_label(extension_dir: Path, manifest: dict[str, Any], key: str) -> str:
    value = str(manifest.get(key) or "").strip()
    if not value:
        return ""

    messages = _load_locale_messages(extension_dir, str(manifest.get("default_locale") or ""))
    if not messages:
        return "" if CHROME_I18N_MESSAGE_RE.fullmatch(value) else value

    def replace_message(match: re.Match[str]) -> str:
        message_key = match.group(1)
        message = _resolve_locale_message(messages, message_key)
        return message if message is not None else match.group(0)

    resolved = CHROME_I18N_MESSAGE_RE.sub(replace_message, value).strip()
    if CHROME_I18N_MESSAGE_RE.fullmatch(resolved):
        return ""
    return resolved


def _load_locale_messages(extension_dir: Path, default_locale: str) -> dict[str, Any]:
    locale_root = extension_dir / "_locales"
    if not locale_root.is_dir():
        return {}

    preferred_locales = [
        default_locale,
        default_locale.split("_", 1)[0] if default_locale else "",
        "en_US",
        "en",
    ]
    for locale in [item for item in preferred_locales if item]:
        messages = _read_locale_file(locale_root / locale / "messages.json")
        if messages:
            return messages

    for messages_path in sorted(locale_root.glob("*/messages.json")):
        messages = _read_locale_file(messages_path)
        if messages:
            return messages
    return {}


def _read_locale_file(messages_path: Path) -> dict[str, Any]:
    if not messages_path.is_file():
        return {}
    try:
        data = json.loads(messages_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_locale_message(messages: dict[str, Any], key: str) -> str | None:
    entry = messages.get(key)
    if not isinstance(entry, dict):
        return None
    message = str(entry.get("message") or "")
    if not message:
        return None

    placeholders = entry.get("placeholders")
    if isinstance(placeholders, dict):
        for name, placeholder in placeholders.items():
            if not isinstance(placeholder, dict):
                continue
            content = str(placeholder.get("content") or "")
            if not content:
                continue
            message = re.sub(
                rf"\${re.escape(str(name))}\$",
                content,
                message,
                flags=re.IGNORECASE,
            )
    return message
