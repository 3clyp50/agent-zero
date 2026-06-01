from helpers.api import ApiHandler, Request
from plugins._browser.helpers.chromium import describe_chromium_binary
from plugins._browser.helpers.config import build_browser_launch_config, get_browser_config
from plugins._browser.helpers.playwright import (
    get_playwright_binary,
    get_playwright_cache_dir,
    get_playwright_cache_dirs,
)
from plugins._browser.helpers.runtime import known_context_ids


class Status(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        browser_config = get_browser_config()
        launch_config = build_browser_launch_config(browser_config)
        compatibility_binary = get_playwright_binary()
        chromium = describe_chromium_binary()
        try:
            from plugins._a0_connector.helpers.ws_runtime import all_host_browser_metadata
        except ImportError:
            host_browser = {"connectors": []}
        else:
            host_browser = {"connectors": all_host_browser_metadata()}
        return {
            "plugin": "_browser",
            "runtime": {
                "backend": "container_cdp",
                "control": "cdp",
                "browser": "chromium",
                "visual_transport": "cdp-screencast",
                "launch_mode": launch_config["browser_mode"],
            },
            "chromium": {
                **chromium,
                "launch_mode": launch_config["browser_mode"],
            },
            "playwright": {
                "cache_dir": get_playwright_cache_dir(),
                "cache_dirs": [str(path) for path in get_playwright_cache_dirs()],
                "binary_found": bool(compatibility_binary),
                "install_required": False,
                "binary_path": str(compatibility_binary) if compatibility_binary else "",
                "chromium_binary_path": str(compatibility_binary) if compatibility_binary else "",
                "purpose": "compatibility",
            },
            "host_browser": host_browser,
            "contexts": known_context_ids(),
        }
