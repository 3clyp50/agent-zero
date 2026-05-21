import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))



def test_websocket_harness_entrypoint_is_present_in_developer_settings_template():
    dev_template_path = (
        PROJECT_ROOT
        / "webui"
        / "components"
        / "settings"
        / "developer"
        / "dev.html"
    )
    content = dev_template_path.read_text(encoding="utf-8")
    assert "websocket-tester.html" in content
    assert "websocket-event-console.html" in content
    assert "!$store.settings.additional?.is_dockerized" in content


def test_websocket_harness_template_is_gated_by_runtime():
    template_path = PROJECT_ROOT / "webui" / "components" / "settings" / "developer" / "websocket-tester.html"
    content = template_path.read_text(encoding="utf-8")
    assert "window.runtimeInfo?.isDevelopment" in content
    assert "$store.root?.isDevelopment" not in content


def test_timezone_settings_section_is_present():
    store_path = PROJECT_ROOT / "webui" / "components" / "settings" / "settings-store.js"
    agent_settings_path = PROJECT_ROOT / "webui" / "components" / "settings" / "agent" / "agent-settings.html"
    locale_path = PROJECT_ROOT / "webui" / "components" / "settings" / "agent" / "locale.html"

    store = store_path.read_text(encoding="utf-8")
    agent_settings = agent_settings_path.read_text(encoding="utf-8")
    assert "section-locale" in store
    assert "section-voice" in store
    assert "settings/agent/locale.html" in agent_settings
    assert store.index("section-models-summary") < store.index("section-locale")
    assert store.index("section-locale") < store.index("section-agent-plugins")
    assert agent_settings.index("section-models-summary") < agent_settings.index("section-locale")
    assert agent_settings.index("section-locale") < agent_settings.index("section-agent-plugins")
    assert agent_settings.rindex("section-locale") < agent_settings.rindex("section-agent-plugins")
    locale = locale_path.read_text(encoding="utf-8")
    assert "Automatic (browser)" in locale
    assert "$store.settings.settings.timezone" in locale
    assert "12-hour (AM/PM)" in locale
    assert "24-hour" in locale
    assert "$store.settings.settings.time_format" in locale
