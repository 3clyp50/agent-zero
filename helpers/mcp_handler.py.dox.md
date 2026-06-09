# mcp_handler.py DOX

## Purpose

- Own the `mcp_handler.py` helper module.
- This module loads global and project-scoped MCP server configuration and exposes MCP tools to agents.
- Keep this file-level DOX profile synchronized with `mcp_handler.py` because this directory is intentionally flat.

## Ownership

- `mcp_handler.py` owns the runtime implementation.
- `mcp_handler.py.dox.md` owns durable notes about responsibilities, contracts, side effects, and verification for that implementation.
- Classes:
- `MCPTool` (`Tool`)
  - `get_log_object(self) -> LogItem`
  - `async execute(self, **kwargs)`
  - `async before_execution(self, **kwargs)`
  - `async after_execution(self, response: Response, **kwargs)`
- `MCPServerRemote` (`BaseModel`)
  - `get_error(self) -> str`
  - `get_log(self) -> str`
  - `get_tools(self) -> List[dict[str, Any]]`
  - `has_tool(self, tool_name: str) -> bool`
  - `async call_tool(self, tool_name: str, input_data: Dict[str, Any]) -> CallToolResult`
  - `update(self, config: dict[str, Any]) -> 'MCPServerRemote'`
  - `async initialize(self) -> 'MCPServerRemote'`
- `MCPServerLocal` (`BaseModel`)
  - `get_error(self) -> str`
  - `get_log(self) -> str`
  - `get_tools(self) -> List[dict[str, Any]]`
  - `has_tool(self, tool_name: str) -> bool`
  - `async call_tool(self, tool_name: str, input_data: Dict[str, Any]) -> CallToolResult`
  - `update(self, config: dict[str, Any]) -> 'MCPServerLocal'`
  - `async initialize(self) -> 'MCPServerLocal'`
- `MCPConfig` (`BaseModel`)
  - `get_instance(cls) -> 'MCPConfig'`
  - `clear_project_instances(cls)`
  - `parse_config_string(cls, config_str: str) -> List[Dict[str, Any]]`
  - `merge_config_strings(cls, global_config: str, project_config: str) -> tuple[List[Dict[str, Any]], str]`
  - `get_project_instance(cls, project_name: str | None, *, force: bool = False) -> 'MCPConfig'`
  - `refresh_project(cls, project_name: str) -> 'MCPConfig'`
  - `get_for_agent(cls, agent: Any) -> 'MCPConfig'`
  - `wait_for_lock(cls)`
  - `update(cls, config_str: str) -> Any`
  - `normalize_config(cls, servers: Any)`
  - `get_server_log(self, server_name: str) -> str`
  - `get_servers_status(self) -> list[dict[str, Any]]`
  - `get_server_detail(self, server_name: str) -> dict[str, Any]`
  - `is_initialized(self) -> bool`
- `MCPClientBase` (`ABC`)
  - `async update_tools(self) -> 'MCPClientBase'`
  - `has_tool(self, tool_name: str) -> bool`
  - `get_tools(self) -> List[dict[str, Any]]`
  - `async call_tool(self, tool_name: str, input_data: Dict[str, Any]) -> CallToolResult`
  - `get_log(self)`
- `MCPClientLocal` (`MCPClientBase`)
- `CustomHTTPClientFactory` (`ABC`)
- `MCPClientRemote` (`MCPClientBase`)
  - `get_session_id(self) -> Optional[str]`
- Top-level functions:
- `_mcp_get(item: Any, key: str, default: Any=...) -> Any`
- `normalize_name(name: str) -> str`
- `_determine_server_type(config_dict: dict) -> str`: Determine the server type based on configuration, with backward compatibility.
- `_is_streaming_http_type(server_type: str) -> bool`: Check if the server type is a streaming HTTP variant.
- `_split_qualified_tool_name(tool_name: str) -> tuple[str, str]`: Split `server.tool` names while preserving dots inside MCP tool names.
- `initialize_mcp(mcp_servers_config: str)`
- Notable constants/configuration names: `DEFAULT_MCP_SERVERS_CONFIG`, `MCP_MEDIA_TOKENS_ESTIMATE`, `MAX_MCP_RESOURCE_TEXT_CHARS`, `T`.

## Runtime Contracts

- Helper modules own reusable framework APIs and must preserve public callers unless all callers, tests, and docs are updated together.
- Update this file whenever public functions, classes, persistence behavior, path/security assumptions, side effects, or cross-module contracts change.
- `MCPTool` is a `Tool`.
- `MCPTool` defines `execute(...)`.
- Global MCP configuration remains backed by settings; project MCP configuration is loaded through `helpers.projects` and merged with global config when an active agent context has `context.project`.
- Project-scoped MCP servers overlay global servers by normalized name. The resulting `MCPConfig` cache key is derived from both config strings so project instances refresh when either scope changes.
- Server status and detail responses include `scope`, and MCP tools resolve through `MCPConfig.get_for_agent(agent)` before execution.
- MCP tool names are qualified as `server_name.tool_name`; server names are normalized without dots, and the tool portion may contain dots.
- Server-specific `init_timeout` and `tool_timeout` override global MCP client timeout settings for list-tools and call-tool operations.
- Server status marks initialized server objects with cached initialization errors as disconnected, even if the config object exists.
- Observed side-effect areas: filesystem writes, network calls, WebSocket state, settings/state persistence, secret handling.
- Imported dependency areas include: `abc`, `anyio.streams.memory`, `asyncio`, `contextlib`, `datetime`, `helpers`, `helpers.log`, `helpers.print_style`, `helpers.tool`, `httpx`, `json`, `mcp`, `mcp.client.sse`, `mcp.client.stdio`, `mcp.client.streamable_http`, `mcp.shared.message`.

## Key Concepts

- Important called helpers/classes observed in the source: `TypeVar`, `name.strip.lower`, `re.sub`, `Field`, `PrivateAttr`, `threading.Lock`, `_split_qualified_tool_name`, `config_dict.lower`, `server_type.lower`, `MCPConfig.get_instance.is_initialized`, `MCPConfig.get_for_agent`, `projects.validate_project_name`, `projects.load_project_mcp_servers`, `settings.get_settings`, `self.agent.context.log.log`, `str.strip`, `media_artifacts.guess_extension`, `callable`, `self._content_item_dump`, `join`, `Response`, `self.get_log_object`, `self._raw_tool_response`, `additional.pop`, `self._coerce_media_token_estimate`.
- Keep request/response, tool, or helper semantics documented here at the same time as source changes.

## Work Guidance

- Preserve public helper APIs used by core code and plugins unless every caller is updated.
- Keep path, auth, secret, persistence, network, and subprocess behavior explicit and bounded.
- Prefer adding cohesive helper functions here only when behavior is reused across modules.

## Verification

- Run targeted tests for changed helper behavior; run security regressions for auth, filesystem, WebSocket, tunnel, upload, or secret-handling helpers.
- Related tests observed by source search:
  - `tests/test_mcp_handler_multimodal.py`

## Child DOX Index

No child DOX files.
