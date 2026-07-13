from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read(*parts: str) -> str:
    return PROJECT_ROOT.joinpath(*parts).read_text(encoding="utf-8")


def test_model_config_text_buttons_have_shared_primitive() -> None:
    buttons_css = read("webui", "css", "buttons.css")
    preset_modal = read("plugins", "_model_config", "webui", "main.html")
    config_modal = read("plugins", "_model_config", "webui", "config.html")

    assert ".text-button {" in buttons_css
    assert "appearance: none;" in buttons_css
    assert ".text-button:hover:not(:disabled)" in buttons_css
    assert ".text-button .material-symbols-outlined" in buttons_css
    assert 'class="text-button preset-add-btn"' in preset_modal
    assert 'class="text-button preset-delete-btn"' in preset_modal
    assert 'class="text-button"' in config_modal


def test_model_preset_rows_keep_stable_identity_after_middle_delete() -> None:
    preset_modal = read("plugins", "_model_config", "webui", "main.html")
    preset_store = read("plugins", "_model_config", "webui", "model-config-store.js")

    assert 'x-data="$store.modelConfig.createPresetEditor()"' in preset_modal
    assert ':key="preset._key"' in preset_modal
    assert "createPresetEditor()" in preset_store
    assert "_key: nextPresetKey++" in preset_store
    assert "removePreset(index)" in preset_store
    assert ':key="idx"' not in preset_modal
    assert "JSON.parse(JSON.stringify" not in preset_modal
    assert "presets.splice" not in preset_modal


def test_model_preset_editor_can_reset_to_bundled_defaults() -> None:
    preset_modal = read("plugins", "_model_config", "webui", "main.html")
    preset_store = read("plugins", "_model_config", "webui", "model-config-store.js")

    assert '$confirmClick($event, () => resetPresets())' in preset_modal
    assert "Reset to default" in preset_modal
    assert "async resetPresets()" in preset_store
    assert "if (!await store.resetGlobalPresets()) return;" in preset_store
    assert "this.refreshPresets();" in preset_store
    assert "refreshPresets();" in preset_modal


def test_plugin_settings_reset_is_explicit_and_does_not_capture_toast_early() -> None:
    settings_modal = read("webui", "components", "plugins", "plugin-settings.html")
    settings_store = read("webui", "components", "plugins", "plugin-settings-store.js")

    assert "Reset to default" in settings_modal
    assert "const justToast = globalThis.justToast" not in settings_store
    assert 'globalThis.justToast?.("Settings reset to default.", "info")' in settings_store
