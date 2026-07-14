from __future__ import annotations

import asyncio
import uuid

from plugins._a0_connector.api.v1 import launcher_gateway_control
from plugins._a0_connector.api.v1.capabilities import _feature_list
from plugins._a0_connector.api.v1.launcher_gateway_status import LauncherGatewayStatus
from plugins._a0_connector.api.ws_connector import WS_FEATURES
from plugins._a0_connector.helpers import ws_runtime


def _sid(label: str) -> str:
    return f"gateway-{label}-{uuid.uuid4()}"


def _gateway(gateway_id: str, *, files: bool = True) -> dict:
    return {
        "version": 1,
        "kind": "launcher",
        "id": gateway_id,
        "host_label": "Test host",
        "state": "connected",
        "master_enabled": True,
        "scopes": {
            "files": files,
            "code_execution": True,
            "browser": True,
            "computer_use": True,
        },
    }


def test_launcher_gateway_features_are_negotiated_on_http_and_websocket() -> None:
    assert "launcher_gateway" in _feature_list()
    assert "launcher_gateway_control" in WS_FEATURES
    assert LauncherGatewayStatus.requires_auth() is True


def test_launcher_gateway_is_fallback_after_context_bound_cli() -> None:
    context_id = f"ctx-{uuid.uuid4()}"
    cli_sid = _sid("cli")
    gateway_sid = _sid("launcher")
    ws_runtime.register_sid(cli_sid)
    ws_runtime.register_sid(gateway_sid)
    ws_runtime.subscribe_sid_to_context(cli_sid, context_id)
    ws_runtime.store_sid_launcher_gateway_metadata(gateway_sid, _gateway("installation-a"))
    try:
        assert ws_runtime.remote_tool_sids_for_context(context_id)[:2] == [
            cli_sid,
            gateway_sid,
        ]
    finally:
        ws_runtime.unregister_sid(cli_sid)
        ws_runtime.unregister_sid(gateway_sid)


def test_distinct_launcher_gateways_fail_closed() -> None:
    first_sid = _sid("first")
    second_sid = _sid("second")
    ws_runtime.register_sid(first_sid)
    ws_runtime.register_sid(second_sid)
    ws_runtime.store_sid_launcher_gateway_metadata(first_sid, _gateway("installation-a"))
    ws_runtime.store_sid_launcher_gateway_metadata(second_sid, _gateway("installation-b"))
    try:
        status = ws_runtime.launcher_gateway_status()
        assert status["state"] == "multiple_hosts"
        assert status["connected"] is False
        assert ws_runtime.active_launcher_gateway_sid() is None
        assert first_sid not in ws_runtime.remote_tool_sids_for_context("unbound")
        assert second_sid not in ws_runtime.remote_tool_sids_for_context("unbound")
    finally:
        ws_runtime.unregister_sid(first_sid)
        ws_runtime.unregister_sid(second_sid)


def test_duplicate_gateway_identity_replaces_stale_socket() -> None:
    stale_sid = _sid("stale")
    fresh_sid = _sid("fresh")
    ws_runtime.register_sid(stale_sid)
    ws_runtime.register_sid(fresh_sid)
    ws_runtime.store_sid_launcher_gateway_metadata(stale_sid, _gateway("installation-a"))
    ws_runtime.store_sid_launcher_gateway_metadata(fresh_sid, _gateway("installation-a"))
    try:
        assert ws_runtime.active_launcher_gateway_sid() == fresh_sid
        assert ws_runtime.store_sid_launcher_gateway_metadata(
            stale_sid,
            _gateway("installation-a"),
        ) is None
    finally:
        ws_runtime.unregister_sid(stale_sid)
        ws_runtime.unregister_sid(fresh_sid)


def test_gateway_disables_code_execution_when_files_are_off() -> None:
    sid = _sid("scope")
    ws_runtime.register_sid(sid)
    ws_runtime.store_sid_launcher_gateway_metadata(sid, _gateway("installation-a", files=False))
    try:
        gateway = ws_runtime.launcher_gateway_status()["gateway"]
        assert gateway["scopes"]["files"] is False
        assert gateway["scopes"]["code_execution"] is False
    finally:
        ws_runtime.unregister_sid(sid)


def test_gateway_status_metadata_is_bounded() -> None:
    sid = _sid("bounded")
    payload = _gateway("installation-a")
    payload["status"] = {
        "browser": {
            "message": "x" * 4000,
            "available_browsers": [{"browser_id": f"browser-{index}"} for index in range(100)],
        },
        "computer_use": {
            "capabilities": {"elements": {"tree_backends": ["ax", "at-spi"]}}
        },
    }
    ws_runtime.register_sid(sid)
    ws_runtime.store_sid_launcher_gateway_metadata(sid, payload)
    try:
        status = ws_runtime.launcher_gateway_status()["gateway"]["status"]
        assert len(status["browser"]["message"]) == 2048
        assert len(status["browser"]["available_browsers"]) == 64
        assert status["computer_use"]["capabilities"]["elements"]["tree_backends"] == [
            "ax",
            "at-spi",
        ]
    finally:
        ws_runtime.unregister_sid(sid)


def test_gateway_control_requires_csrf_and_waits_for_ack(monkeypatch) -> None:
    sid = _sid("control")
    ws_runtime.register_sid(sid)
    ws_runtime.store_sid_launcher_gateway_metadata(sid, _gateway("installation-a"))

    class FakeManager:
        async def emit_to(self, namespace, target_sid, event, data, **kwargs):
            assert namespace == "/ws"
            assert target_sid == sid
            assert event == "connector_gateway_control"
            updated = _gateway("installation-a")
            updated["master_enabled"] = False
            updated["state"] = "paused"
            ws_runtime.resolve_pending_gateway_control(
                data["request_id"],
                sid=sid,
                payload={
                    "request_id": data["request_id"],
                    "ok": True,
                    "gateway": updated,
                },
            )

    monkeypatch.setattr(launcher_gateway_control, "get_shared_ws_manager", lambda: FakeManager())
    handler = launcher_gateway_control.LauncherGatewayControl(None, None)
    try:
        result = asyncio.run(handler.process({"action": "set_master", "enabled": False}, None))
        assert handler.requires_auth() is True
        assert handler.requires_csrf() is True
        assert result["ok"] is True
        assert result["status"]["gateway"]["master_enabled"] is False
    finally:
        ws_runtime.unregister_sid(sid)


def test_gateway_control_acknowledgement_timeout(monkeypatch) -> None:
    sid = _sid("timeout")
    ws_runtime.register_sid(sid)
    ws_runtime.store_sid_launcher_gateway_metadata(sid, _gateway("installation-a"))

    class SilentManager:
        async def emit_to(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(launcher_gateway_control, "get_shared_ws_manager", lambda: SilentManager())
    monkeypatch.setattr(launcher_gateway_control, "_CONTROL_TIMEOUT_SECONDS", 0.01)
    handler = launcher_gateway_control.LauncherGatewayControl(None, None)
    try:
        result = asyncio.run(handler.process({"action": "set_master", "enabled": False}, None))
        assert result.status_code == 504
    finally:
        ws_runtime.unregister_sid(sid)


def test_gateway_emergency_disconnect_returns_acknowledged_disconnected_state(monkeypatch) -> None:
    sid = _sid("emergency")
    ws_runtime.register_sid(sid)
    ws_runtime.store_sid_launcher_gateway_metadata(sid, _gateway("installation-a"))

    class FakeManager:
        async def emit_to(self, _namespace, target_sid, event, data, **_kwargs):
            assert target_sid == sid
            assert event == "connector_gateway_control"
            assert data["action"] == "emergency_disconnect"
            updated = _gateway("installation-a")
            updated["state"] = "disconnected"
            ws_runtime.resolve_pending_gateway_control(
                data["request_id"],
                sid=sid,
                payload={
                    "request_id": data["request_id"],
                    "ok": True,
                    "gateway": updated,
                },
            )

    monkeypatch.setattr(launcher_gateway_control, "get_shared_ws_manager", lambda: FakeManager())
    handler = launcher_gateway_control.LauncherGatewayControl(None, None)
    try:
        result = asyncio.run(handler.process({"action": "emergency_disconnect"}, None))
        assert result["ok"] is True
        assert result["status"]["state"] == "disconnected"
    finally:
        ws_runtime.unregister_sid(sid)
