# A0 Connector Plugin DOX

## Purpose

- Own the current Agent Zero connector plugin for HTTP and WebSocket integration.
- Provide remote execution, text-editing freshness, and connector runtime bridges.

## Ownership

- `plugin.yaml` owns plugin metadata and settings scope.
- `api/` owns connector WebSocket and API entry points.
- `helpers/` owns chat context, event bridge, execution config, freshness, version, and WebSocket runtime helpers.
- `tools/`, `prompts/`, `skills/`, `extensions/`, and `webui/` own connector-facing agent and UI contributions.

## Local Contracts

- Preserve session-auth and `auth.handlers` activation assumptions.
- Keep remote tool prompts synchronized with remote tool behavior and disclose
  them only from connected CLI metadata: no connected CLI hides all remote tool
  prompts, remote file metadata enables `text_editor_remote`, F4-enabled remote
  execution metadata enables `code_execution_remote`, and supported enabled
  Computer Use that does not need re-arming enables `computer_use_remote`.
- Do not bypass WebSocket authentication or leak connector session data.
- Advertise Launcher gateways additively through HTTP capability
  `launcher_gateway` and WebSocket feature `launcher_gateway_control`. Older
  ordinary CLI clients retain their existing protocol fields and behavior; do
  not provide a partial tools-only fallback when either feature is absent.
- A Launcher `connector_hello` carries a versioned gateway object with kind,
  stable ID, host label, and bounded status. Store it per authenticated socket,
  remove it on disconnect, and let context-bound CLI sockets retain routing
  priority. One unique Launcher gateway may be the global fallback. A duplicate
  socket with the same ID replaces stale state; distinct simultaneous IDs fail
  closed as Multiple hosts.
- `connector_gateway_control` and `connector_gateway_control_result` cover
  master state, complete scope replacement, and Disconnect
  (`emergency_disconnect` on the wire). Protected
  WebUI mutations require CSRF, await the matching acknowledgement, and return
  refreshed status. Never let the WebUI select a host folder or personal
  browser profile.
- Launcher gateway scopes expose file reading and writing separately. File
  writing depends on reading, and Code execution depends on file writing. Keep
  older gateway declarations without `file_write` read/write compatible.
- The `sync-status-end` Launcher gateway extension renders only when the user agent
  includes `A0-Launcher/`. It may show status, master/scope controls,
  preparation errors, and Disconnect; standard browser sessions must
  not expose it. Keep its trigger inside the existing sync indicator, render one
  computer glyph per connected Launcher gateway, and retain one muted glyph
  while disconnected so the control remains reachable. Do not add a native
  tooltip, visible status label, count badge, or animated expansion.
  Keep the open popover above the compact right-canvas rail and report control
  failures through the shared notification system. Use the standard WebUI
  border-radius tokens for its controls and popover.
- File operation results may arrive as chunked JSON/base64
  `connector_file_op_result` frames; resolve the pending file operation only
  after all chunks for the `op_id` are assembled.
- Host browser status metadata may advertise `available_browsers` entries with browser ids, labels, CDP endpoints, status, and enabled state; keep older CLI payloads without those fields compatible.

## Work Guidance

- Coordinate connector runtime changes with API, tools, prompts, and WebUI viewer behavior together.

## Verification

- Run connector-specific tests or smoke-test HTTP and `/ws` integration when changing runtime behavior.
- Launcher gateway regression coverage lives in
  `tests/test_a0_connector_launcher_gateway.py`.

## Child DOX Index

No child DOX files.
