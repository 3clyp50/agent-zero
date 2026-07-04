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
- File operation results may arrive as chunked JSON/base64
  `connector_file_op_result` frames; resolve the pending file operation only
  after all chunks for the `op_id` are assembled.
- Host browser status metadata may advertise `available_browsers` entries with browser ids, labels, CDP endpoints, status, and enabled state; keep older CLI payloads without those fields compatible.

## Work Guidance

- Coordinate connector runtime changes with API, tools, prompts, and WebUI viewer behavior together.

## Verification

- Run connector-specific tests or smoke-test HTTP and `/ws` integration when changing runtime behavior.

## Child DOX Index

No child DOX files.
