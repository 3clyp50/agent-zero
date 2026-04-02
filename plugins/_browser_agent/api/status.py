import importlib.metadata

from helpers.api import ApiHandler, Request, Response
from helpers import plugins
from plugins._browser_agent.helpers.playwright import (
    get_playwright_binary,
    get_playwright_cache_dir,
)
from plugins._browser_agent.helpers.browser_llm import get_browser_model_config


class Status(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        plugin_cfg = plugins.get_plugin_config("_browser_agent") or {}
        browser_mode = str(plugin_cfg.get("browser_model_mode", "main")).strip().lower()
        browser_model_cfg = plugin_cfg.get("browser_model", {})
        browser_model_custom = bool(
            isinstance(browser_model_cfg, dict)
            and (browser_model_cfg.get("provider") or browser_model_cfg.get("name"))
        )
        cfg = get_browser_model_config()
        binary = get_playwright_binary()

        browser_use_ok = False
        browser_use_error = ""
        browser_use_version = ""
        try:
            import browser_use  # noqa: F401

            browser_use_ok = True
            browser_use_version = importlib.metadata.version("browser-use")
        except Exception as e:
            browser_use_error = str(e)

        if browser_mode == "custom" and browser_model_custom:
            model_source = "Custom Browser model"
        elif browser_mode == "custom":
            model_source = "Custom Browser model not configured, using Main model"
        else:
            model_source = "Use Main model (default)"

        return {
            "plugin": "_browser_agent",
            "model_source": model_source,
            "browser_model_mode": browser_mode,
            "browser_model_custom": browser_model_custom,
            "model": {
                "provider": cfg.get("provider", ""),
                "name": cfg.get("name", ""),
                "vision": bool(cfg.get("vision", False)),
            },
            "playwright": {
                "cache_dir": get_playwright_cache_dir(),
                "binary_found": bool(binary),
                "binary_path": str(binary) if binary else "",
            },
            "browser_use": {
                "import_ok": browser_use_ok,
                "version": browser_use_version,
                "error": browser_use_error,
            },
        }
