import json
import os
from copy import deepcopy

from helpers.extension import Extension
from helpers import files, plugins, yaml as yaml_helper
from helpers.print_style import PrintStyle


class MigrateModelConfig(Extension):
    """
    One-time migration: copy legacy model settings into _model_config plugin config.
    Runs during initialize_migration. Only migrates if no global plugin config exists yet
    and the settings file contains legacy model fields.
    """

    LEGACY_FIELDS = [
        "chat_model_provider", "chat_model_name", "chat_model_api_base",
        "chat_model_kwargs", "chat_model_ctx_length", "chat_model_vision",
        "chat_model_rl_requests", "chat_model_rl_input", "chat_model_rl_output",
        "chat_model_ctx_history",
        "util_model_provider", "util_model_name", "util_model_api_base",
        "util_model_kwargs", "util_model_ctx_length",
        "util_model_rl_requests", "util_model_rl_input", "util_model_rl_output",
        "util_model_ctx_input",
        "embed_model_provider", "embed_model_name", "embed_model_api_base",
        "embed_model_kwargs", "embed_model_rl_requests", "embed_model_rl_input",
        "browser_model_provider", "browser_model_name", "browser_model_api_base",
        "browser_model_vision", "browser_model_rl_requests", "browser_model_rl_input",
        "browser_model_rl_output", "browser_model_kwargs", "browser_http_headers",
    ]
    CONFIG_SECTIONS = ("chat_model", "utility_model", "embedding_model")
    PRESET_SECTIONS = ("chat", "utility", "embedding")
    VENICE_KWARGS = {
        "a0_api_mode": "chat",
        "venice_parameters": {"include_venice_system_prompt": False},
    }

    def execute(self, **kwargs):
        self._repair_saved_venice_config()

        # Check if global plugin config already exists
        global_config_path = files.get_abs_path(
            files.USER_DIR, files.PLUGINS_DIR, "_model_config", plugins.CONFIG_FILE_NAME
        )
        if os.path.exists(global_config_path):
            return  # already migrated or manually configured

        # Read raw settings file to check for legacy model fields
        settings_file = files.get_abs_path("usr/settings.json")
        if not os.path.exists(settings_file):
            return

        try:
            raw = json.loads(files.read_file(settings_file))
        except Exception:
            return

        # Check if any legacy model field exists in the raw settings
        has_legacy = any(field in raw for field in self.LEGACY_FIELDS)
        if not has_legacy:
            return

        # Build plugin config from legacy settings
        plugin_config = {
            "allow_chat_override": False,
            "chat_model": {
                "provider": raw.get("chat_model_provider", "openrouter"),
                "name": raw.get("chat_model_name", ""),
                "api_base": raw.get("chat_model_api_base", ""),
                "ctx_length": raw.get("chat_model_ctx_length", 128000),
                "ctx_history": raw.get("chat_model_ctx_history", 0.7),
                "vision": raw.get("chat_model_vision", True),
                "rl_requests": raw.get("chat_model_rl_requests", 0),
                "rl_input": raw.get("chat_model_rl_input", 0),
                "rl_output": raw.get("chat_model_rl_output", 0),
                "kwargs": raw.get("chat_model_kwargs", {}),
            },
            "utility_model": {
                "provider": raw.get("util_model_provider", "openrouter"),
                "name": raw.get("util_model_name", ""),
                "api_base": raw.get("util_model_api_base", ""),
                "ctx_length": raw.get("util_model_ctx_length", 128000),
                "ctx_input": raw.get("util_model_ctx_input", 0.7),
                "rl_requests": raw.get("util_model_rl_requests", 0),
                "rl_input": raw.get("util_model_rl_input", 0),
                "rl_output": raw.get("util_model_rl_output", 0),
                "kwargs": raw.get("util_model_kwargs", {}),
            },
            "embedding_model": {
                "provider": raw.get("embed_model_provider", "huggingface"),
                "name": raw.get("embed_model_name", "sentence-transformers/all-MiniLM-L6-v2"),
                "api_base": raw.get("embed_model_api_base", ""),
                "rl_requests": raw.get("embed_model_rl_requests", 0),
                "rl_input": raw.get("embed_model_rl_input", 0),
                "kwargs": raw.get("embed_model_kwargs", {}),
            },
        }

        # Ensure kwargs are dicts (might be strings from .env format)
        for section in ["chat_model", "utility_model", "embedding_model"]:
            kw = plugin_config[section].get("kwargs")
            if isinstance(kw, str):
                plugin_config[section]["kwargs"] = {}

        self._repair_venice_config_slots(plugin_config)

        # Save as global plugin config
        plugins.save_plugin_config("_model_config", "", "", plugin_config)
        PrintStyle(background_color="#6734C3", font_color="white", padding=True).print(
            "Migrated legacy model settings to _model_config plugin config."
        )

    def _repair_saved_venice_config(self):
        changed = False
        config_path = files.get_abs_path(
            files.USER_DIR, files.PLUGINS_DIR, "_model_config", plugins.CONFIG_FILE_NAME
        )
        presets_path = files.get_abs_path(
            files.USER_DIR, files.PLUGINS_DIR, "_model_config", "presets.yaml"
        )

        if os.path.exists(config_path):
            try:
                config = json.loads(files.read_file(config_path))
            except Exception:
                config = None
            if isinstance(config, dict) and self._repair_venice_config_slots(config):
                files.write_file(config_path, json.dumps(config))
                changed = True

        if os.path.exists(presets_path):
            try:
                presets = yaml_helper.loads(files.read_file(presets_path))
            except Exception:
                presets = None
            if isinstance(presets, list) and self._repair_venice_presets(presets):
                files.write_file(presets_path, yaml_helper.dumps(presets))
                changed = True

        if changed:
            PrintStyle(background_color="#6734C3", font_color="white", padding=True).print(
                "Updated saved Venice model settings for chat completions."
            )

    def _repair_venice_config_slots(self, config: dict) -> bool:
        changed = False
        for section in self.CONFIG_SECTIONS:
            changed = self._repair_venice_slot(config.get(section)) or changed
        return changed

    def _repair_venice_presets(self, presets: list) -> bool:
        changed = False
        for preset in presets:
            if not isinstance(preset, dict):
                continue
            for section in self.PRESET_SECTIONS:
                changed = self._repair_venice_slot(preset.get(section)) or changed
            if not any(section in preset for section in self.PRESET_SECTIONS):
                changed = self._repair_venice_slot(preset) or changed
        return changed

    def _repair_venice_slot(self, slot) -> bool:
        if not isinstance(slot, dict):
            return False
        provider = str(slot.get("provider") or "").strip().lower()
        if provider != "venice":
            return False
        if slot.get("kwargs") == self.VENICE_KWARGS:
            return False
        slot["kwargs"] = deepcopy(self.VENICE_KWARGS)
        return True
