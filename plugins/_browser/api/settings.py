from types import SimpleNamespace

from helpers import plugins
from helpers.api import ApiHandler, Request
from plugins._browser.helpers.config import (
    AUTOFOCUS_ACTIVE_PAGE_KEY,
    DEFAULT_HOMEPAGE_KEY,
    MODEL_PRESET_KEY,
    PLUGIN_NAME,
    get_browser_config,
    get_browser_main_model_summary,
    get_browser_model_preset_options,
)


class Settings(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "get")
        agent = self._agent_from_input(input)

        if action in {"get", "list"}:
            return self._browser_settings_payload(agent=agent)

        if action == "set_model_preset":
            preset_name = str(input.get(MODEL_PRESET_KEY, "") or "").strip()
            available_presets = {
                option["name"]
                for option in get_browser_model_preset_options(agent=agent)
                if option.get("name") and not option.get("missing")
            }
            if preset_name and preset_name not in available_presets:
                return {"ok": False, "error": "Choose an available browser model preset."}

            config = get_browser_config()
            config[MODEL_PRESET_KEY] = preset_name
            plugins.save_plugin_config(PLUGIN_NAME, "", "", config)
            return self._browser_settings_payload(agent=agent)

        return {"ok": False, "error": f"Unknown action: {action}"}

    def _agent_from_input(self, input: dict):
        context_id = str(input.get("context_id", "") or "").strip()
        if not context_id:
            return None
        try:
            context = self.use_context(context_id, create_if_not_exists=False)
        except Exception:
            return None
        config = getattr(context, "config", None)
        if config is None:
            return None
        return SimpleNamespace(context=context, config=config)

    def _browser_settings_payload(self, agent=None) -> dict:
        config = get_browser_config()
        return {
            "ok": True,
            DEFAULT_HOMEPAGE_KEY: config[DEFAULT_HOMEPAGE_KEY],
            AUTOFOCUS_ACTIVE_PAGE_KEY: config[AUTOFOCUS_ACTIVE_PAGE_KEY],
            MODEL_PRESET_KEY: config[MODEL_PRESET_KEY],
            "main_model_summary": get_browser_main_model_summary(agent=agent),
            "model_preset_options": get_browser_model_preset_options(agent=agent, settings=config),
        }
