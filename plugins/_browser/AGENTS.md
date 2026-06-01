# Browser Plugin DOX

## Purpose

- Own Agent Zero's bundled Browser plugin: the agent-facing `browser` tool, Browser Canvas/modal surface, settings UI, CDP runtime, host-browser bridge, browser skills, and browser prompt context.
- Keep Browser small, reliable, and visible through Agent Zero's own Canvas/modal affordance rather than a desktop/Xpra browser window.
- Preserve the default architecture: headless Chromium controlled by CDP, with a CDP screencast rendered into the Browser surface.

## Ownership

- `plugin.yaml` and `default_config.yaml` own plugin metadata and default Browser settings.
- `tools/browser.py` owns the agent tool action contract, tool result formatting, selector/ref resolution, and tool-history screenshot metadata.
- `helpers/runtime.py` owns the container Browser runtime, tab registry, CDP action dispatch, downloads, screenshots, screencasts, viewport sync, clipboard bridge, and context cleanup.
- `helpers/cdp.py` owns direct Chrome DevTools Protocol process launch, websocket command/event handling, target/page attachment, page input, screenshots, script injection, downloads, and CDP sessions.
- `helpers/chromium.py` and `helpers/playwright.py` own Chromium/headless-shell discovery and compatibility cache migration; they must not make Playwright the browser controller.
- `helpers/config.py`, `api/settings.py`, `webui/config.html`, and `webui/browser-config-store.js` own Browser settings normalization, persistence, and settings UI.
- `api/ws_browser.py` owns Browser viewer WebSocket commands, subscriptions, frame streaming, runtime warmup, snapshots, inputs, and annotation requests.
- `api/status.py` owns Browser runtime status, Chromium readiness, active runtime listing, and host-browser connector status summaries.
- `helpers/connector_runtime.py` owns A0 CLI host-browser routing, privacy policy enforcement, host artifact handling, and connector error shaping.
- `assets/browser-dom-helper.js` and `assets/browser-page-content.js` own DOM capture, ref generation, annotation metadata, and page-side action helpers.
- `webui/browser-panel.html`, `webui/browser-store.js`, and `webui/main.html` own Browser tabs, address bar, navigation controls, annotation UI, keyboard/mouse forwarding, Canvas/modal handoff, and frame rendering.
- `extensions/webui/` owns Browser surface registration, right Canvas panel insertion, tool-result rendering, and already-open Browser surface synchronization.
- `extensions/python/` owns prompt context, runtime cleanup on context reset/remove/disconnect, WebSocket routing, and startup cache migration.
- `prompts/agent.system.tool.browser.md` and `skills/` own model-facing Browser guidance and specialized Browser automation workflows.

## Local Contracts

- Default runtime is `runtime_backend: "container"`: headless Chromium/headless shell controlled directly by CDP.
- The visible Browser belongs in Agent Zero's Browser Canvas/modal surface. Do not route the default Browser viewer through Desktop, Xpra, VNC, or a low-framerate GUI browser window.
- Playwright may be used only as a compatibility source for cached Chromium/headless-shell binaries and migration helpers. Do not reintroduce Playwright as the Browser control plane.
- Do not reintroduce Chrome extension support. Retired extension APIs, helpers, skills, settings affordances, `extension_paths`, `--load-extension`, and full-Chromium requirements must stay removed.
- Container Browser launches must prefer `A0_BROWSER_CHROMIUM_BINARY`, system Chromium/headless-shell candidates, or the migrated `tmp/playwright` headless-shell cache. Do not bundle full Chromium in the repository.
- `hooks.py` may install missing framework-runtime Python dependencies needed by Browser, because self-updated instances must work without a fresh Docker image pull.
- Browser sessions are scoped to chat context ids. Runtime state belongs under temporary Browser session/cache paths or `usr/downloads/browser`; user-owned downloads must stay out of plugin source.
- The Browser tab cap is enforced by `max_open_tabs`; opening over the limit should raise a repairable error that tells the agent to reuse or close tabs.
- Browser tab ids and context ids are part of the UI contract. Canvas/modal tab switching, the `+` button, and tab `X` close controls must keep working in both surfaces.
- CDP target attach must remain serialized and race-aware. Self-created tabs should attach immediately; discovered/popup targets should not duplicate tabs or block `new_page()` behind target-created handlers.
- New URL opens should create the CDP target at the requested URL when possible, then hand off visual loading quickly instead of waiting for slow page completion.
- Browser tool `open`, `navigate`, `back`, `forward`, and `reload` should not block on automatic static history screenshots. Explicit screenshots remain available through the `screenshot` action.
- Browser screenshots are not automatically model-visible. Tool guidance must continue telling the agent to call `vision_load` with returned paths when visual reasoning is needed.
- The Browser surface must not auto-open from tool results. It may sync an already-open Browser surface to focused actions when `autofocus_active_page` allows it.
- WebSocket payloads must keep `context_id`, `browser_id`, `viewer_id`, `browsers`, `state`, `viewer`, and `frame_source` semantics stable for frontend consumers.
- Canvas and modal rendering use CDP screencast frames; frame queues should favor the newest frame and acknowledge CDP frames promptly to keep navigation smooth.
- Viewport sync must preserve responsive page layout: use explicit viewport dimensions from the visible Browser surface and restart streams when the viewport remounts.
- Host-browser mode is opt-in through settings and A0 CLI connector metadata. Respect `host_browser_privacy_policy` before returning host page content or screenshots.
- Browser settings UI must use the plugin settings prototype pattern, bind persisted values through `config.*`, and avoid inline success/error boxes in favor of existing notification flows.
- Browser UI should use the existing Canvas, modal, toolbar, tab, and notification idioms; keep labels user-facing and avoid backend jargon unless the user must recognize a setting.

## Work Guidance

- Read `tests/test_browser_agent_regressions.py` before changing Browser behavior; it is the main contract suite for this plugin.
- When adding or changing a Browser action, update `tools/browser.py`, `helpers/runtime.py`, the tool prompt, Browser skills, and regression tests together.
- When changing settings, update `default_config.yaml`, `helpers/config.py`, `api/settings.py`, `webui/config.html`, `webui/browser-config-store.js`, and tests together.
- When touching CDP launch, target attachment, navigation waits, screencasts, screenshots, or viewport sync, test both direct runtime calls and the live Browser Canvas/modal path.
- Prefer DOM/CDP refs and structured page helpers over coordinate-only actions. Coordinate forwarding is for visual/manual interactions and fallback cases.
- Keep host-browser bridge changes isolated to `helpers/connector_runtime.py` and connector metadata contracts unless container Browser behavior truly needs to change too.
- Keep startup/cache migration idempotent. Browser cleanup may remove retired Browser-owned caches, but must not delete user files or unrelated runtime state.
- Keep prompt and skill wording aligned with the product shape: CDP-first Browser, Browser Canvas/modal viewer, explicit screenshots, no Chrome extensions.

## Verification

- Run focused Browser regressions after Browser plugin changes:
  ```bash
  conda run -n a0 pytest tests/test_browser_agent_regressions.py -q
  ```
- Run syntax checks for touched Browser Python/JS files:
  ```bash
  python -m py_compile plugins/_browser/helpers/cdp.py plugins/_browser/helpers/runtime.py plugins/_browser/api/ws_browser.py plugins/_browser/tools/browser.py
  node --check plugins/_browser/webui/browser-store.js
  ```
- For runtime, WebSocket, or visible Browser changes, mirror the repo into the live Docker runtime at `localhost:32080`, restart it, and smoke-test:
  - Browser Canvas `+` creates exactly one tab.
  - Browser Canvas tab `X` closes the tab.
  - Browser modal/window `+` and tab `X` work.
  - A natural prompt such as `Visit openrouter.com` opens a visible Browser tab without a long apparent hang.
- Sweep recent container logs for tracebacks, CDP errors, WebSocket errors, and frontend runtime warnings after live Browser tests.

## Child DOX Index

No child DOX files.
