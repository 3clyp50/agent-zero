# projects.py DOX

## Purpose

- Own the `projects.py` helper module.
- This module owns project metadata, workspace creation, Git status, and project-scoped settings including per-project MCP server config.
- Keep this file-level DOX profile synchronized with `projects.py` because this directory is intentionally flat.

## Ownership

- `projects.py` owns the runtime implementation.
- `projects.py.dox.md` owns durable notes about responsibilities, contracts, side effects, and verification for that implementation.
- Classes:
- `FileStructureInjectionSettings` (`TypedDict`)
- `SubAgentSettings` (`TypedDict`)
- `BasicProjectData` (`TypedDict`)
- `GitStatusData` (`TypedDict`)
- `EditProjectData` (`BasicProjectData`)
- Top-level functions:
- `get_projects_parent_folder()`
- `get_project_folder(name: str)`
- `get_project_meta(name: str, *sub_dirs)`
- `validate_project_name(name: str | None) -> str`
- `delete_project(name: str)`
- `create_project(name: str, data: BasicProjectData)`
- `clone_git_project(name: str, git_url: str, git_token: str, data: BasicProjectData)`: Clone a git repository as a new A0 project. Token is used only for cloning via http header.
- `load_project_header(name: str)`
- `_default_file_structure_settings()`
- `_normalizeBasicData(data: BasicProjectData) -> BasicProjectData`
- `_normalizeEditData(data: EditProjectData) -> EditProjectData`
- `_edit_data_to_basic_data(data: EditProjectData)`
- `_basic_data_to_edit_data(data: BasicProjectData) -> EditProjectData`
- `update_project(name: str, data: EditProjectData)`
- `load_basic_project_data(name: str) -> BasicProjectData`
- `load_edit_project_data(name: str) -> EditProjectData`
- `save_project_header(name: str, data: BasicProjectData)`
- `load_project_llm_data(name: str) -> dict`
- `save_project_llm_settings(name: str, llm_data: object)`
- `load_project_mcp_servers(name: str) -> str`
- `save_project_mcp_servers(name: str, mcp_servers: str)`
- `get_active_projects_list()`
- `_get_projects_list(parent_dir)`
- `activate_project(context_id: str, name: str, mark_dirty: bool=...)`
- `deactivate_project(context_id: str, mark_dirty: bool=...)`
- `reactivate_project_in_chats(name: str)`
- `deactivate_project_in_chats(name: str)`
- `build_system_prompt_vars(name: str)`
- `get_additional_instructions_files(name: str)`
- `get_project_instruction_files(name: str, include_agents_md: bool=...) -> list[tuple[str, str]]`
- `get_project_agents_md_instruction_file(name: str) -> tuple[str, str] | None`
- `_format_project_instruction_files(instruction_files: list[tuple[str, str]]) -> str`
- `_normalize_include_agents_md(value: object) -> bool`
- Notable constants/configuration names: `PROJECTS_PARENT_DIR`, `PROJECT_META_DIR`, `PROJECT_INSTRUCTIONS_DIR`, `PROJECT_KNOWLEDGE_DIR`, `PROJECT_HEADER_FILE`, `PROJECT_MCP_SERVERS_FILE`, `PROJECT_AGENTS_MD_FILES`, `DEFAULT_MCP_SERVERS_CONFIG`, `CONTEXT_DATA_KEY_PROJECT`.

## Runtime Contracts

- Helper modules own reusable framework APIs and must preserve public callers unless all callers, tests, and docs are updated together.
- Update this file whenever public functions, classes, persistence behavior, path/security assumptions, side effects, or cross-module contracts change.
- Per-project MCP server configuration is persisted as `.a0proj/mcp_servers.json`, exposed through `load_edit_project_data(...)`, and saved during project create/clone/update flows.
- Project MCP config uses the same JSON string shape as global MCP settings: an object with `mcpServers`.
- Project MCP load/save paths validate project names as simple folder basenames before touching `.a0proj/mcp_servers.json`.
- Observed side-effect areas: filesystem reads, filesystem writes, filesystem deletion, plugin state, settings/state persistence, secret handling.
- Imported dependency areas include: `helpers`, `helpers.print_style`, `os`, `typing`.

## Key Concepts

- Important called helpers/classes observed in the source: `files.get_abs_path`, `files.delete_dir`, `deactivate_project_in_chats`, `files.create_dir_safe`, `create_project_meta_folders`, `_normalizeBasicData`, `save_project_header`, `save_project_mcp_servers`, `load_project_mcp_servers`, `save_project_llm_settings`, `files.basename`, `dirty_json.parse`, `FileStructureInjectionSettings`, `cast`, `_normalizeEditData`, `load_edit_project_data`, `_edit_data_to_basic_data`, `save_project_variables`, `save_project_secrets`, `save_project_subagents`, `reactivate_project_in_chats`, `load_basic_project_data`.
- Keep request/response, tool, or helper semantics documented here at the same time as source changes.

## Work Guidance

- Preserve public helper APIs used by core code and plugins unless every caller is updated.
- Keep path, auth, secret, persistence, network, and subprocess behavior explicit and bounded.
- Prefer adding cohesive helper functions here only when behavior is reused across modules.

## Verification

- Run targeted tests for changed helper behavior; run security regressions for auth, filesystem, WebSocket, tunnel, upload, or secret-handling helpers.
- Related tests observed by source search:
  - `tests/test_model_config_project_presets.py`
  - `tests/test_office_document_store.py`
  - `tests/test_plugin_activation_ui.py`
  - `tests/test_projects.py`
  - `tests/test_skills_runtime.py`
  - `tests/test_task_scheduler_timezone.py`
  - `tests/test_time_travel.py`
  - `tests/test_tool_action_contracts.py`

## Child DOX Index

No child DOX files.
