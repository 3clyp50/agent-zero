import asyncio
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import plugins._browser_agent.helpers.browser_llm as browser_llm
import plugins._browser_agent.helpers.browser_use_monkeypatch as browser_use_monkeypatch
import plugins._browser_agent.tools.browser_agent as browser_agent_module


def test_gemini_clean_and_conform_normalizes_known_single_action_shapes():
    raw = (
        '{"action":['
        '{"complete_task":{"title":"T","response":"R","page_summary":"S"}}'
        ']}'
    )

    cleaned = browser_use_monkeypatch.gemini_clean_and_conform(raw)

    assert cleaned is not None
    parsed = json.loads(cleaned)
    assert parsed["action"] == [
        {
            "done": {
                "success": True,
                "data": {
                    "title": "T",
                    "response": "R",
                    "page_summary": "S",
                },
            }
        },
    ]


class DummyBrowserSession:
    def __init__(self) -> None:
        self.kill_called = False
        self.close_called = False

    async def kill(self) -> None:
        self.kill_called = True

    async def close(self) -> None:
        self.close_called = True


class DummyAgent:
    def __init__(self) -> None:
        self.context = SimpleNamespace(id="ctx", task=None)


def test_browser_model_config_defaults_to_main_model(monkeypatch):
    monkeypatch.setattr(
        browser_llm.plugins,
        "get_plugin_config",
        lambda *args, **kwargs: {
            "browser_model_mode": "main",
            "browser_model": {
                "provider": "openrouter",
                "name": "cheap-browser",
                "vision": False,
            },
        },
    )
    monkeypatch.setattr(
        browser_llm.model_config,
        "get_chat_model_config",
        lambda agent=None: {
            "provider": "openrouter",
            "name": "main-model",
            "vision": True,
        },
    )

    cfg = browser_llm.get_browser_model_config(DummyAgent())

    assert cfg["name"] == "main-model"
    assert cfg["vision"] is True


def test_browser_model_config_uses_custom_browser_model_when_enabled(monkeypatch):
    monkeypatch.setattr(
        browser_llm.plugins,
        "get_plugin_config",
        lambda *args, **kwargs: {
            "browser_model_mode": "custom",
            "browser_model": {
                "provider": "openrouter",
                "name": "cheap-browser",
                "vision": False,
            },
        },
    )
    monkeypatch.setattr(
        browser_llm.model_config,
        "get_chat_model_config",
        lambda agent=None: {
            "provider": "openrouter",
            "name": "main-model",
            "vision": True,
        },
    )

    cfg = browser_llm.get_browser_model_config(DummyAgent())

    assert cfg["name"] == "cheap-browser"
    assert cfg["vision"] is False


def test_browser_vision_tracks_effective_browser_model(monkeypatch):
    monkeypatch.setattr(
        browser_agent_module,
        "get_browser_model_config",
        lambda agent=None: {"vision": False},
    )

    state = browser_agent_module.State(DummyAgent())

    assert state._get_browser_vision() is False


def test_build_browser_model_for_agent_uses_effective_browser_model(monkeypatch):
    monkeypatch.setattr(
        browser_llm,
        "get_browser_model_config",
        lambda agent=None: {
            "provider": "openrouter",
            "name": "cheap-browser",
            "api_base": "",
            "vision": False,
        },
    )
    captured = {}

    def fake_build_browser_model_from_config(model_config):
        captured["model_config"] = model_config
        return model_config

    monkeypatch.setattr(
        browser_llm,
        "build_browser_model_from_config",
        fake_build_browser_model_from_config,
    )

    result = browser_llm.build_browser_model_for_agent(DummyAgent())

    assert result.name == "cheap-browser"
    assert captured["model_config"].name == "cheap-browser"


def test_browser_session_teardown_prefers_kill_for_keep_alive_sessions():
    state = browser_agent_module.State(DummyAgent())
    session = DummyBrowserSession()
    state.browser_session = session

    state.kill_task()

    assert session.kill_called is True
    assert session.close_called is False


def test_browser_cleanup_extensions_follow_new_extensible_path_layout():
    extension = importlib.import_module("helpers.extension")
    remove_classes = extension._get_extension_classes(  # type: ignore[attr-defined]
        "_functions/agent/AgentContext/remove/start"
    )
    reset_classes = extension._get_extension_classes(  # type: ignore[attr-defined]
        "_functions/agent/AgentContext/reset/start"
    )

    assert any(cls.__name__ == "CleanupBrowserStateOnRemove" for cls in remove_classes)
    assert any(cls.__name__ == "CleanupBrowserStateOnReset" for cls in reset_classes)
