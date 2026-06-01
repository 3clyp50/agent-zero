from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

import aiohttp


DEFAULT_CDP_CONNECT_TIMEOUT_SECONDS = 15.0
DEFAULT_CDP_COMMAND_TIMEOUT_SECONDS = 30.0
DEFAULT_VIEWPORT = {"width": 1024, "height": 768}
DEVTOOLS_ACTIVE_PORT = "DevToolsActivePort"
CDP_HEADLESS_LAUNCH_ARGS = (
    "--headless=new",
)
CDP_RUNTIME_LAUNCH_ARGS = (
    "--remote-debugging-address=127.0.0.1",
    "--remote-debugging-port=0",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--force-color-profile=srgb",
)


class CDPError(RuntimeError):
    pass


class CDPConnection:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._next_id = 1
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._send_lock = asyncio.Lock()
        self._event_handlers: dict[tuple[str | None, str], list[Callable[[dict[str, Any]], Any]]] = {}

    async def connect(self) -> None:
        timeout = aiohttp.ClientTimeout(total=DEFAULT_CDP_CONNECT_TIMEOUT_SECONDS)
        self._session = aiohttp.ClientSession(timeout=timeout)
        try:
            self._ws = await self._session.ws_connect(
                self.endpoint,
                timeout=DEFAULT_CDP_CONNECT_TIMEOUT_SECONDS,
                autoclose=True,
                autoping=True,
            )
        except Exception:
            await self.close()
            raise
        self._reader_task = asyncio.create_task(self._read_loop())

    def on(
        self,
        method: str,
        callback: Callable[[dict[str, Any]], Any],
        *,
        session_id: str | None = None,
    ) -> None:
        key = (session_id, str(method or ""))
        self._event_handlers.setdefault(key, []).append(callback)

    def off(
        self,
        method: str,
        callback: Callable[[dict[str, Any]], Any],
        *,
        session_id: str | None = None,
    ) -> None:
        key = (session_id, str(method or ""))
        handlers = self._event_handlers.get(key)
        if not handlers:
            return
        with contextlib.suppress(ValueError):
            handlers.remove(callback)
        if not handlers:
            self._event_handlers.pop(key, None)

    async def command(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        session_id: str | None = None,
        timeout: float = DEFAULT_CDP_COMMAND_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        if self._ws is None:
            raise CDPError("Chrome DevTools connection is not open.")
        async with self._send_lock:
            msg_id = self._next_id
            self._next_id += 1
            future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
            self._pending[msg_id] = future
            payload: dict[str, Any] = {"id": msg_id, "method": method}
            if params is not None:
                payload["params"] = params
            if session_id:
                payload["sessionId"] = session_id
            await self._ws.send_json(payload)
        try:
            response = await asyncio.wait_for(future, timeout=max(0.1, float(timeout)))
        finally:
            self._pending.pop(msg_id, None)
        if "error" in response:
            error = response.get("error") or {}
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise CDPError(str(message or f"CDP command failed: {method}"))
        result = response.get("result")
        return result if isinstance(result, dict) else {}

    async def close(self) -> None:
        if self._reader_task is not None:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._reader_task
            self._reader_task = None
        if self._ws is not None:
            with contextlib.suppress(Exception):
                await self._ws.close()
            self._ws = None
        if self._session is not None:
            with contextlib.suppress(Exception):
                await self._session.close()
            self._session = None
        self._fail_pending("Chrome DevTools connection closed.")
        self._event_handlers.clear()

    async def _read_loop(self) -> None:
        assert self._ws is not None
        try:
            async for message in self._ws:
                if message.type == aiohttp.WSMsgType.TEXT:
                    try:
                        payload = json.loads(message.data)
                    except Exception:
                        continue
                    msg_id = payload.get("id")
                    if isinstance(msg_id, int):
                        future = self._pending.get(msg_id)
                        if future is not None and not future.done():
                            future.set_result(payload)
                        continue
                    self._dispatch_event(payload)
                elif message.type in {aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR}:
                    break
        finally:
            self._fail_pending("Chrome DevTools connection closed.")

    def _dispatch_event(self, payload: dict[str, Any]) -> None:
        method = str(payload.get("method") or "")
        if not method:
            return
        params = payload.get("params")
        event_payload = params if isinstance(params, dict) else {}
        session_id = payload.get("sessionId")
        keys = [
            (str(session_id), method) if session_id else None,
            (None, method),
        ]
        for key in keys:
            if key is None:
                continue
            for handler in list(self._event_handlers.get(key, [])):
                try:
                    result = handler(event_payload)
                    if asyncio.iscoroutine(result):
                        asyncio.create_task(result)
                except Exception:
                    continue

    def _fail_pending(self, message: str) -> None:
        for future in list(self._pending.values()):
            if not future.done():
                future.set_result({"error": {"message": message}})
        self._pending.clear()


class CDPSession:
    def __init__(self, connection: CDPConnection, session_id: str) -> None:
        self.connection = connection
        self.session_id = session_id
        self._detached = False

    def on(self, event: str, callback: Callable[[dict[str, Any]], Any]) -> None:
        self.connection.on(event, callback, session_id=self.session_id)

    async def send(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float = DEFAULT_CDP_COMMAND_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        if self._detached:
            raise CDPError("Chrome DevTools session is detached.")
        return await self.connection.command(
            method,
            params,
            session_id=self.session_id,
            timeout=timeout,
        )

    async def detach(self) -> None:
        if self._detached:
            return
        self._detached = True
        with contextlib.suppress(Exception):
            await self.connection.command("Target.detachFromTarget", {"sessionId": self.session_id})


class CDPMouse:
    def __init__(self, page: "CDPPage") -> None:
        self.page = page
        self._x = 0.0
        self._y = 0.0
        self._button = "left"

    async def move(self, x: float, y: float, steps: int | None = None) -> None:
        steps = max(1, int(steps or 1))
        start_x, start_y = self._x, self._y
        for step in range(1, steps + 1):
            next_x = start_x + (float(x) - start_x) * step / steps
            next_y = start_y + (float(y) - start_y) * step / steps
            self._x = next_x
            self._y = next_y
            await self.page.send(
                "Input.dispatchMouseEvent",
                {
                    "type": "mouseMoved",
                    "x": next_x,
                    "y": next_y,
                    "button": "none",
                    "modifiers": self.page.keyboard.modifier_mask,
                },
            )

    async def click(self, x: float, y: float, button: str = "left") -> None:
        await self.move(float(x), float(y))
        await self.down(button=button, click_count=1)
        await self.up(button=button, click_count=1)

    async def dblclick(self, x: float, y: float, button: str = "left") -> None:
        await self.move(float(x), float(y))
        await self.down(button=button, click_count=2)
        await self.up(button=button, click_count=2)

    async def down(self, button: str = "left", *, click_count: int = 1) -> None:
        self._button = _cdp_mouse_button(button)
        await self.page.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mousePressed",
                "x": self._x,
                "y": self._y,
                "button": self._button,
                "buttons": _cdp_mouse_buttons(self._button),
                "clickCount": int(click_count),
                "modifiers": self.page.keyboard.modifier_mask,
            },
        )

    async def up(self, button: str | None = None, *, click_count: int = 1) -> None:
        resolved_button = _cdp_mouse_button(button or self._button)
        await self.page.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseReleased",
                "x": self._x,
                "y": self._y,
                "button": resolved_button,
                "buttons": 0,
                "clickCount": int(click_count),
                "modifiers": self.page.keyboard.modifier_mask,
            },
        )

    async def wheel(self, delta_x: float, delta_y: float) -> None:
        await self.page.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseWheel",
                "x": self._x,
                "y": self._y,
                "deltaX": float(delta_x),
                "deltaY": float(delta_y),
                "modifiers": self.page.keyboard.modifier_mask,
            },
        )


class CDPKeyboard:
    _MODIFIER_BITS = {"Alt": 1, "Control": 2, "Meta": 4, "Shift": 8}
    _ALIASES = {
        "cmd": "Meta",
        "command": "Meta",
        "control": "Control",
        "ctrl": "Control",
        "esc": "Escape",
        "option": "Alt",
        "return": "Enter",
        "space": " ",
    }
    _KEYS = {
        "Alt": ("AltLeft", 18),
        "ArrowDown": ("ArrowDown", 40),
        "ArrowLeft": ("ArrowLeft", 37),
        "ArrowRight": ("ArrowRight", 39),
        "ArrowUp": ("ArrowUp", 38),
        "Backspace": ("Backspace", 8),
        "Control": ("ControlLeft", 17),
        "Delete": ("Delete", 46),
        "End": ("End", 35),
        "Enter": ("Enter", 13),
        "Escape": ("Escape", 27),
        "Home": ("Home", 36),
        "Meta": ("MetaLeft", 91),
        "PageDown": ("PageDown", 34),
        "PageUp": ("PageUp", 33),
        "Shift": ("ShiftLeft", 16),
        "Tab": ("Tab", 9),
        " ": ("Space", 32),
    }

    def __init__(self, page: "CDPPage") -> None:
        self.page = page
        self._pressed: set[str] = set()

    @property
    def modifier_mask(self) -> int:
        mask = 0
        for key in self._pressed:
            mask |= self._MODIFIER_BITS.get(key, 0)
        return mask

    async def type(self, text: str) -> None:
        await self.insert_text(text)

    async def insert_text(self, text: str) -> None:
        await self.page.send("Input.insertText", {"text": str(text or "")})

    async def press(self, key: str) -> None:
        keys = self._split_chord(key)
        if not keys:
            return
        if len(keys) == 1:
            await self.down(keys[0])
            await self.up(keys[0])
            return
        pressed: list[str] = []
        try:
            for modifier in keys[:-1]:
                await self.down(modifier)
                pressed.append(modifier)
            await self.down(keys[-1])
            await self.up(keys[-1])
        finally:
            for modifier in reversed(pressed):
                with contextlib.suppress(Exception):
                    await self.up(modifier)

    async def down(self, key: str) -> None:
        normalized = self._normalize_key(key)
        await self.page.send("Input.dispatchKeyEvent", self._event_params(normalized, "keyDown"))
        if normalized in self._MODIFIER_BITS:
            self._pressed.add(normalized)

    async def up(self, key: str) -> None:
        normalized = self._normalize_key(key)
        await self.page.send("Input.dispatchKeyEvent", self._event_params(normalized, "keyUp"))
        self._pressed.discard(normalized)

    def _event_params(self, key: str, event_type: str) -> dict[str, Any]:
        code, virtual_key = self._key_code(key)
        text = key if len(key) == 1 and not self._text_suppressed() and event_type == "keyDown" else ""
        return {
            "type": event_type,
            "key": key,
            "code": code,
            "windowsVirtualKeyCode": virtual_key,
            "nativeVirtualKeyCode": virtual_key,
            "text": text,
            "unmodifiedText": text,
            "modifiers": self.modifier_mask,
        }

    def _text_suppressed(self) -> bool:
        return bool({"Alt", "Control", "Meta"} & self._pressed)

    @classmethod
    def _split_chord(cls, key: str) -> list[str]:
        return [cls._normalize_key(part) for part in re.split(r"\s*\+\s*", str(key or "")) if part.strip()]

    @classmethod
    def _normalize_key(cls, key: str) -> str:
        raw = str(key or "").strip()
        if len(raw) == 1:
            return raw.upper() if raw.isalpha() else raw
        lowered = raw.lower()
        if lowered in cls._ALIASES:
            return cls._ALIASES[lowered]
        return raw

    @classmethod
    def _key_code(cls, key: str) -> tuple[str, int]:
        if key in cls._KEYS:
            return cls._KEYS[key]
        if len(key) == 1 and key.isalpha():
            upper = key.upper()
            return f"Key{upper}", ord(upper)
        if len(key) == 1 and key.isdigit():
            return f"Digit{key}", ord(key)
        if len(key) == 1:
            return key, ord(key)
        return key, 0


class CDPJSHandle:
    def __init__(self, page: "CDPPage", remote: dict[str, Any]) -> None:
        self.page = page
        self.remote = remote

    def as_element(self) -> "CDPJSHandle | None":
        return self if self.remote.get("objectId") else None

    async def set_input_files(self, paths: list[str]) -> None:
        object_id = str(self.remote.get("objectId") or "")
        if not object_id:
            raise CDPError("CDP handle does not reference a DOM object.")
        with contextlib.suppress(Exception):
            await self.page.send("DOM.enable", {})
        described = await self.page.send("DOM.describeNode", {"objectId": object_id})
        node = described.get("node") if isinstance(described.get("node"), dict) else {}
        backend_node_id = node.get("backendNodeId")
        if not backend_node_id:
            raise CDPError("CDP could not resolve a backend node for file upload.")
        await self.page.send(
            "DOM.setFileInputFiles",
            {
                "files": [str(path) for path in paths],
                "backendNodeId": int(backend_node_id),
            },
        )

    async def dispose(self) -> None:
        object_id = str(self.remote.get("objectId") or "")
        if object_id:
            with contextlib.suppress(Exception):
                await self.page.send("Runtime.releaseObject", {"objectId": object_id})


class CDPPage:
    def __init__(self, context: "CDPContext", target_id: str, session: CDPSession, url: str = "") -> None:
        self.context = context
        self.connection = context.connection
        self.target_id = target_id
        self.session = session
        self.session_id = session.session_id
        self.url = url or "about:blank"
        self.mouse = CDPMouse(self)
        self.keyboard = CDPKeyboard(self)
        self.viewport_size = dict(DEFAULT_VIEWPORT)
        self._handlers: dict[str, list[Callable[[], Any]]] = {}
        self._closed = False

    def on(self, event: str, callback: Callable[..., Any]) -> None:
        self._handlers.setdefault(str(event or ""), []).append(callback)

    async def send(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float = DEFAULT_CDP_COMMAND_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        return await self.session.send(method, params, timeout=timeout)

    async def start_navigation(self, url: str) -> dict[str, Any]:
        result = await self.send("Page.navigate", {"url": url})
        self.url = url
        return result

    async def goto(self, url: str, **_: object) -> None:
        result = await self.start_navigation(url)
        if result.get("errorText"):
            return
        await self.wait_for_load_state("domcontentloaded", timeout=30000)

    async def go_back(self, **_: object) -> None:
        await self._navigate_history(-1)

    async def go_forward(self, **_: object) -> None:
        await self._navigate_history(1)

    async def reload(self, **_: object) -> None:
        await self.send("Page.reload", {})
        await self.wait_for_load_state("domcontentloaded", timeout=15000)

    async def wait_for_load_state(self, *_: object, timeout: int | float = 5000, **__: object) -> None:
        deadline = time.monotonic() + max(0.1, float(timeout) / 1000.0)
        while time.monotonic() < deadline:
            try:
                state = await self.evaluate("() => document.readyState")
                if str(state or "") in {"interactive", "complete"}:
                    return
            except Exception:
                pass
            await asyncio.sleep(0.05)

    async def bring_to_front(self) -> None:
        await self.connection.command("Target.activateTarget", {"targetId": self.target_id})

    async def title(self) -> str:
        result = await self.evaluate("() => document.title")
        return str(result or "")

    async def current_url(self) -> str:
        with contextlib.suppress(Exception):
            current = await self.evaluate("() => location.href")
            if current:
                self.url = str(current)
        return self.url

    async def evaluate(self, script: str, arg: object = None) -> object:
        result = await self.send(
            "Runtime.evaluate",
            {
                "expression": _cdp_evaluate_expression(script, arg),
                "awaitPromise": True,
                "returnByValue": True,
            },
        )
        if result.get("exceptionDetails"):
            raise CDPError(_exception_message(result["exceptionDetails"]))
        remote = result.get("result") if isinstance(result.get("result"), dict) else {}
        if "value" in remote:
            return remote.get("value")
        if remote.get("type") == "undefined":
            return None
        return remote.get("description")

    async def evaluate_handle(self, script: str, arg: object = None) -> CDPJSHandle:
        result = await self.send(
            "Runtime.evaluate",
            {
                "expression": _cdp_evaluate_expression(script, arg),
                "awaitPromise": True,
                "returnByValue": False,
            },
        )
        if result.get("exceptionDetails"):
            raise CDPError(_exception_message(result["exceptionDetails"]))
        remote = result.get("result") if isinstance(result.get("result"), dict) else {}
        return CDPJSHandle(self, remote)

    async def screenshot(self, **kwargs: object) -> bytes:
        image_type = str(kwargs.get("type") or "jpeg")
        params: dict[str, Any] = {"format": image_type}
        if image_type == "jpeg":
            params["quality"] = int(kwargs.get("quality") or 80)
        if kwargs.get("full_page"):
            with contextlib.suppress(Exception):
                metrics = await self.send("Page.getLayoutMetrics", {})
                content_size = metrics.get("cssContentSize") or metrics.get("contentSize") or {}
                width = max(1, int(content_size.get("width") or self.viewport_size["width"]))
                height = max(1, int(content_size.get("height") or self.viewport_size["height"]))
                params["captureBeyondViewport"] = True
                params["clip"] = {"x": 0, "y": 0, "width": width, "height": height, "scale": 1}
        result = await self.send("Page.captureScreenshot", params, timeout=60.0)
        data = base64.b64decode(str(result.get("data") or ""))
        path = kwargs.get("path")
        if path:
            Path(str(path)).write_bytes(data)
        return data

    async def set_viewport_size(self, viewport: dict[str, int]) -> None:
        width = max(320, min(4096, int(viewport.get("width") or DEFAULT_VIEWPORT["width"])))
        height = max(200, min(4096, int(viewport.get("height") or DEFAULT_VIEWPORT["height"])))
        self.viewport_size = {"width": width, "height": height}
        await self.send(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": width,
                "height": height,
                "deviceScaleFactor": 1,
                "mobile": False,
                "dontSetVisibleSize": True,
            },
        )
        with contextlib.suppress(Exception):
            await self.send("Emulation.setVisibleSize", {"width": width, "height": height})

    async def set_input_files(self, selector: str, paths: list[str]) -> None:
        handle = await self.evaluate_handle(
            "(selector) => document.querySelector(selector)",
            str(selector or ""),
        )
        try:
            element = handle.as_element()
            if not element:
                raise CDPError(f"Selector {selector!r} did not resolve to an element.")
            await element.set_input_files(paths)
        finally:
            await handle.dispose()

    async def close(self) -> None:
        if self._closed:
            return
        with contextlib.suppress(Exception):
            await self.connection.command("Target.closeTarget", {"targetId": self.target_id})
        self._mark_closed()

    def is_closed(self) -> bool:
        return self._closed

    async def _navigate_history(self, delta: int) -> None:
        history = await self.send("Page.getNavigationHistory", {})
        entries = history.get("entries") if isinstance(history.get("entries"), list) else []
        current_index = int(history.get("currentIndex") or 0)
        target_index = current_index + int(delta)
        if target_index < 0 or target_index >= len(entries):
            return
        entry_id = entries[target_index].get("id")
        if entry_id is None:
            return
        await self.send("Page.navigateToHistoryEntry", {"entryId": int(entry_id)})
        await self.wait_for_load_state("domcontentloaded", timeout=10000)

    def _mark_closed(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._emit("close")

    def _emit(self, event: str) -> None:
        for handler in list(self._handlers.get(event, [])):
            try:
                handler()
            except TypeError:
                with contextlib.suppress(Exception):
                    handler(self)
            except Exception:
                continue


class CDPContext:
    def __init__(self, connection: CDPConnection) -> None:
        self.connection = connection
        self.pages: list[CDPPage] = []
        self._pages_by_target: dict[str, CDPPage] = {}
        self._attach_lock = asyncio.Lock()
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._init_scripts: list[str] = []
        self._default_timeout = 30000
        self._default_navigation_timeout = 30000
        self.connection.on("Target.targetCreated", self._on_target_created)
        self.connection.on("Target.targetDestroyed", self._on_target_destroyed)
        self.connection.on("Target.targetInfoChanged", self._on_target_info_changed)

    async def initialize(self, *, downloads_dir: Path | None = None) -> None:
        with contextlib.suppress(Exception):
            await self.connection.command("Target.setDiscoverTargets", {"discover": True})
        if downloads_dir is not None:
            downloads_dir.mkdir(parents=True, exist_ok=True)
            with contextlib.suppress(Exception):
                await self.connection.command(
                    "Browser.setDownloadBehavior",
                    {"behavior": "allow", "downloadPath": str(downloads_dir)},
                )
        await self.discover_pages()

    def set_default_timeout(self, timeout: int) -> None:
        self._default_timeout = int(timeout)

    def set_default_navigation_timeout(self, timeout: int) -> None:
        self._default_navigation_timeout = int(timeout)

    def on(self, event: str, callback: Callable[..., Any]) -> None:
        self._handlers[str(event or "")] = callback

    async def add_init_script(self, script: str | None = None, *, path: str | None = None) -> None:
        source = script if script is not None else Path(str(path)).read_text(encoding="utf-8")
        self._init_scripts.append(str(source))
        for page in list(self.pages):
            with contextlib.suppress(Exception):
                await page.send("Page.addScriptToEvaluateOnNewDocument", {"source": str(source)})

    async def new_page(self, url: str = "about:blank") -> CDPPage:
        page_url = str(url or "about:blank")
        result = await self.connection.command("Target.createTarget", {"url": page_url})
        target_id = str(result.get("targetId") or "")
        if not target_id:
            raise CDPError("Chromium did not return a target id for the new page.")
        return await self._attach_page(target_id, page_url, emit=False)

    async def new_cdp_session(self, page: CDPPage) -> CDPSession:
        attach = await self.connection.command(
            "Target.attachToTarget",
            {"targetId": page.target_id, "flatten": True},
        )
        session_id = str(attach.get("sessionId") or "")
        if not session_id:
            raise CDPError(f"Could not attach an extra CDP session to target {page.target_id}.")
        return CDPSession(self.connection, session_id)

    async def discover_pages(self) -> list[CDPPage]:
        result = await self.connection.command("Target.getTargets", {})
        infos = result.get("targetInfos") if isinstance(result.get("targetInfos"), list) else []
        visible_targets: set[str] = set()
        for info in infos:
            if not isinstance(info, dict) or info.get("type") != "page":
                continue
            target_id = str(info.get("targetId") or "")
            url = str(info.get("url") or "about:blank")
            if not target_id or not _cdp_target_visible(url):
                continue
            visible_targets.add(target_id)
            page = self._pages_by_target.get(target_id)
            if page is None:
                page = await self._attach_page(target_id, url, emit=False)
            else:
                page.url = url
        for target_id in list(self._pages_by_target):
            if target_id not in visible_targets:
                self._remove_page(target_id)
        self.pages = [page for page in self.pages if page.target_id in self._pages_by_target]
        return list(self.pages)

    async def close(self) -> None:
        for page in list(self.pages):
            with contextlib.suppress(Exception):
                await page.close()

    async def _attach_page(self, target_id: str, url: str, *, emit: bool) -> CDPPage:
        async with self._attach_lock:
            page = self._pages_by_target.get(target_id)
            if page is not None:
                page.url = url or page.url
                return page
            attach = await self.connection.command(
                "Target.attachToTarget",
                {"targetId": target_id, "flatten": True},
            )
            session_id = str(attach.get("sessionId") or "")
            if not session_id:
                raise CDPError(f"Could not attach to Chromium target {target_id}.")
            session = CDPSession(self.connection, session_id)
            page = CDPPage(self, target_id, session, url)
            self._pages_by_target[target_id] = page
            self.pages.append(page)
            self._wire_page_events(page)
            await self._prepare_page(page)
            if emit:
                self._emit("page", page)
            return page

    async def _prepare_page(self, page: CDPPage) -> None:
        for method, params in (
            ("Page.enable", {}),
            ("Runtime.enable", {}),
            ("DOM.enable", {}),
            ("Page.setLifecycleEventsEnabled", {"enabled": True}),
        ):
            with contextlib.suppress(Exception):
                await page.send(method, params)
        for source in self._init_scripts:
            with contextlib.suppress(Exception):
                await page.send("Page.addScriptToEvaluateOnNewDocument", {"source": source})

    def _wire_page_events(self, page: CDPPage) -> None:
        def frame_navigated(params: dict[str, Any]) -> None:
            frame = params.get("frame") if isinstance(params.get("frame"), dict) else {}
            if not frame.get("parentId") and frame.get("url"):
                page.url = str(frame.get("url"))

        def navigated_within_document(params: dict[str, Any]) -> None:
            if params.get("url"):
                page.url = str(params.get("url"))

        self.connection.on("Page.frameNavigated", frame_navigated, session_id=page.session_id)
        self.connection.on("Page.navigatedWithinDocument", navigated_within_document, session_id=page.session_id)

    def _on_target_created(self, params: dict[str, Any]) -> None:
        info = params.get("targetInfo") if isinstance(params.get("targetInfo"), dict) else {}
        if info.get("type") != "page":
            return
        target_id = str(info.get("targetId") or "")
        url = str(info.get("url") or "about:blank")
        if not target_id or not _cdp_target_visible(url) or target_id in self._pages_by_target:
            return
        asyncio.create_task(self._attach_discovered_page(target_id, url))

    async def _attach_discovered_page(self, target_id: str, url: str) -> None:
        await asyncio.sleep(0.05)
        if target_id in self._pages_by_target:
            return
        with contextlib.suppress(Exception):
            await self._attach_page(target_id, url, emit=True)

    def _on_target_destroyed(self, params: dict[str, Any]) -> None:
        target_id = str(params.get("targetId") or "")
        if target_id:
            self._remove_page(target_id)

    def _on_target_info_changed(self, params: dict[str, Any]) -> None:
        info = params.get("targetInfo") if isinstance(params.get("targetInfo"), dict) else {}
        target_id = str(info.get("targetId") or "")
        page = self._pages_by_target.get(target_id)
        if page is not None and info.get("url"):
            page.url = str(info.get("url"))

    def _remove_page(self, target_id: str) -> None:
        page = self._pages_by_target.pop(target_id, None)
        if page is None:
            return
        self.pages = [candidate for candidate in self.pages if candidate.target_id != target_id]
        page._mark_closed()

    def _emit(self, event: str, *args: Any) -> None:
        callback = self._handlers.get(event)
        if not callback:
            return
        try:
            callback(*args)
        except Exception:
            return


class CDPBrowserProcess:
    def __init__(
        self,
        *,
        executable_path: Path,
        profile_dir: Path,
        downloads_dir: Path,
        launch_args: list[str],
        viewport: dict[str, int] | None = None,
        headless: bool = True,
        env: dict[str, str] | None = None,
    ) -> None:
        self.executable_path = executable_path
        self.profile_dir = profile_dir
        self.downloads_dir = downloads_dir
        self.launch_args = launch_args
        self.viewport = viewport or DEFAULT_VIEWPORT
        self.headless = bool(headless)
        self.env = dict(env or {})
        self.process: subprocess.Popen | None = None
        self.connection: CDPConnection | None = None
        self.context: CDPContext | None = None
        self.log_path = self.profile_dir / "chromium-cdp.log"
        self._log_file: Any = None

    async def start(self) -> CDPContext:
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self._clear_devtools_active_port()
        cmd = self._command()
        self._log_file = self.log_path.open("ab")
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=self._log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env={**os.environ, **self.env} if self.env else None,
            )
        except Exception:
            self._close_log_file()
            raise

        endpoint = await self._wait_for_endpoint()
        self.connection = CDPConnection(endpoint)
        try:
            await self.connection.connect()
            self.context = CDPContext(self.connection)
            await self.context.initialize(downloads_dir=self.downloads_dir)
        except Exception:
            await self.close()
            raise
        return self.context

    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    async def close(self) -> None:
        if self.connection is not None:
            with contextlib.suppress(Exception):
                await self.connection.command("Browser.close", {}, timeout=2.0)
            with contextlib.suppress(Exception):
                await self.connection.close()
            self.connection = None
        await self._stop_process()
        self.context = None
        self._close_log_file()

    def _command(self) -> list[str]:
        width = max(320, min(4096, int(self.viewport.get("width") or DEFAULT_VIEWPORT["width"])))
        height = max(200, min(4096, int(self.viewport.get("height") or DEFAULT_VIEWPORT["height"])))
        args = [
            str(self.executable_path),
            f"--user-data-dir={self.profile_dir}",
            f"--window-size={width},{height}",
            *(CDP_HEADLESS_LAUNCH_ARGS if self.headless else ()),
            *CDP_RUNTIME_LAUNCH_ARGS,
            *self.launch_args,
            "about:blank",
        ]
        return _dedupe_chromium_args(args)

    async def _wait_for_endpoint(self) -> str:
        deadline = time.monotonic() + DEFAULT_CDP_CONNECT_TIMEOUT_SECONDS
        active_port_path = self.profile_dir / DEVTOOLS_ACTIVE_PORT
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(
                    "Chromium exited before exposing a DevTools endpoint. "
                    f"Exit code: {self.process.returncode}. Log tail: {self._log_tail()}"
                )
            endpoint = self._read_endpoint(active_port_path)
            if endpoint:
                return endpoint
            await asyncio.sleep(0.05)
        raise RuntimeError(
            "Timed out waiting for Chromium to expose a DevTools endpoint. "
            f"Log tail: {self._log_tail()}"
        )

    def _read_endpoint(self, active_port_path: Path) -> str:
        try:
            lines = active_port_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return ""
        if len(lines) < 2:
            return ""
        port = lines[0].strip()
        path = lines[1].strip()
        if not port.isdigit() or not path:
            return ""
        return f"ws://127.0.0.1:{port}{path}"

    def _clear_devtools_active_port(self) -> None:
        with contextlib.suppress(OSError):
            (self.profile_dir / DEVTOOLS_ACTIVE_PORT).unlink()

    async def _stop_process(self) -> None:
        if self.process is None:
            return
        process = self.process
        self.process = None
        if process.poll() is not None:
            return
        with contextlib.suppress(ProcessLookupError, OSError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            await asyncio.wait_for(asyncio.to_thread(process.wait), timeout=3.0)
            return
        except asyncio.TimeoutError:
            pass
        with contextlib.suppress(ProcessLookupError, OSError):
            os.killpg(process.pid, signal.SIGKILL)
        with contextlib.suppress(Exception):
            await asyncio.to_thread(process.wait)

    def _log_tail(self, limit: int = 2000) -> str:
        try:
            data = self.log_path.read_bytes()[-limit:]
        except OSError:
            return ""
        return data.decode("utf-8", errors="replace").strip()

    def _close_log_file(self) -> None:
        if self._log_file is not None:
            with contextlib.suppress(Exception):
                self._log_file.close()
            self._log_file = None


def _dedupe_chromium_args(args: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for arg in args:
        text = str(arg)
        if not text.startswith("--"):
            output.append(text)
            continue
        key = text.split("=", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def _cdp_mouse_button(button: str) -> str:
    normalized = str(button or "left").strip().lower()
    if normalized == "right":
        return "right"
    if normalized in {"middle", "auxiliary"}:
        return "middle"
    return "left"


def _cdp_mouse_buttons(button: str) -> int:
    if button == "right":
        return 2
    if button == "middle":
        return 4
    return 1


def _cdp_evaluate_expression(script: str, arg: object = None) -> str:
    source = str(script or "undefined")
    if arg is not None:
        return f"({source})({json.dumps(arg)})"
    stripped = source.strip()
    if _cdp_expression_is_iife(stripped):
        return source
    if _cdp_expression_is_function(stripped):
        return f"({source})()"
    return source


def _cdp_expression_is_function(source: str) -> bool:
    return bool(
        re.match(r"^(?:async\s+)?function\b", source)
        or re.match(r"^(?:async\s+)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>", source)
    )


def _cdp_expression_is_iife(source: str) -> bool:
    compact = source.rstrip()
    return compact.endswith(")();") or compact.endswith("})();")


def _cdp_target_visible(url: str) -> bool:
    normalized = str(url or "")
    if normalized in {"", "about:blank", "chrome://newtab/"}:
        return True
    if normalized.startswith("chrome://inspect"):
        return True
    return not normalized.startswith(("chrome://", "chrome-untrusted://", "devtools://"))


def _exception_message(details: Any) -> str:
    if not isinstance(details, dict):
        return str(details)
    exception = details.get("exception")
    if isinstance(exception, dict):
        return str(exception.get("description") or exception.get("value") or details)
    return str(details.get("text") or details)
