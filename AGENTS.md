# Agent Zero - AGENTS.md

[Generated using reconnaissance on 2026-02-22]

## Quick Reference
Tech Stack: Framework Python 3.12+ | Agent execution Python 3.13 in Docker | Flask | Alpine.js | LiteLLM | WebSocket (Socket.io)
Dev Server: python run_ui.py (discover host/port from startup output or runtime configuration; do not assume a default port)
Run Tests: pytest (standard) or pytest tests/test_name.py (file-scoped)
Documentation: README.md | docs/
Frontend & Plugin DOX: [WebUI](webui/AGENTS.md) | [Components](webui/components/AGENTS.md) | [Frontend JS](webui/js/AGENTS.md) | [Plugins](plugins/AGENTS.md)

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Core Commands](#core-commands)
3. [Docker Environment](#docker-environment)
4. [Project Structure](#project-structure)
5. [Development Patterns & Conventions](#development-patterns--conventions)
6. [Safety and Permissions](#safety-and-permissions)
7. [Code Examples](#code-examples)
8. [Git Workflow](#git-workflow)
9. [Release Notes](#release-notes)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

Agent Zero is a dynamic, organic agentic framework designed to grow and learn. It uses the operating system as a tool, featuring a multi-agent cooperation model where every agent can create subordinates to break down tasks.

Type: Full-Stack Agentic Framework (Python Backend + Alpine.js Frontend)
Status: Active Development
Primary Language(s): Python, JavaScript (ES Modules)

---

## Core Commands

### Setup
Do not combine these commands; run them individually:
```bash
pip install -r requirements.txt
```
- Start WebUI: python run_ui.py
- Discover the WebUI URL from startup output, launcher/Docker port mappings, or explicit `--host`/`--port`/`WEB_UI_PORT` configuration; do not hardcode a default port.

---

## Docker Environment

When running in Docker, Agent Zero uses two distinct Python runtimes to isolate the framework itself from code executed on behalf of the agent:

### 1. Framework Runtime (/opt/venv-a0)
- Version: Python 3.12.4
- Purpose: Runs the Agent Zero framework itself: WebUI backend, API, core loop, scheduler, framework imports, and plugin hooks/tools that execute inside the framework process.
- Packages: Contains framework dependencies from requirements.txt.
- Verification: Use this runtime for framework/backend import checks, WebUI startup checks, and plugin hook behavior unless the code explicitly switches environments.

### 2. Agent Execution Runtime (/opt/venv)
- Version: Python 3.13
- Purpose: Default Python environment for the agent's terminal/code-execution tasks and user code run by the agent.
- Behavior: Packages installed by the agent during a task belong here so task dependencies do not pollute or prove the framework runtime. Do not use this runtime as evidence that framework imports, WebUI startup, or plugin hooks work.

---

## Project Structure

```
/
├── agent.py              # Core Agent and AgentContext definitions
├── initialize.py         # Framework initialization logic
├── models.py             # LLM provider configurations
├── run_ui.py             # WebUI server entry point
├── api/                  # API Handlers (ApiHandler subclasses) + WsHandler subclasses (ws_*.py)
├── extensions/           # Backend lifecycle extensions
├── helpers/              # Shared Python utilities (plugins, files, etc.)
├── tools/                # Agent tools (Tool subclasses)
├── webui/
│   ├── components/       # Alpine.js components
│   ├── js/               # Core frontend logic (modals, stores, etc.)
│   └── index.html        # Main UI shell
├── usr/                  # User data directory (isolated from core)
│   ├── plugins/          # Custom user plugins
│   ├── settings.json     # User-specific configuration
│   └── workdir/          # Default agent workspace
├── plugins/              # Core system plugins
├── agents/               # Agent profiles (prompts and config)
├── prompts/              # System and message prompt templates
├── knowledge/
│   └── main/about/       # Agent self-knowledge reference material
│       ├── identity.md           # Philosophy, principles, project context
│       ├── architecture.md       # Agent loop, multi-agent coordination, extensions
│       ├── capabilities.md       # Detailed capabilities and limitations
│       ├── configuration.md      # LLM roles, providers, profiles, plugins, settings
│       └── setup-and-deployment.md  # Docker deployment, updates, troubleshooting
└── tests/                # Pytest suite
```

Key Files:
- agent.py: Defines AgentContext, LoopData virtual prompt areas (Protocol before history and Extras after history), and the main Agent class.
- helpers/plugins.py: Plugin discovery and configuration logic.
- webui/js/AlpineStore.js: Store factory for reactive frontend state.
- helpers/api.py: Base class for all API endpoints.
- models.py: LLM provider configuration and LiteLLM wrappers; framework LiteLLM defaults such as `drop_params=True` are merged with `litellm_global_kwargs`, configured values override framework defaults, documented module-level switches such as `drop_params` are applied to LiteLLM, and merged kwargs are passed per call.
- scripts/openrouter_release_notes_system_prompt.md: Editable system prompt used to generate GitHub release notes during Docker publishing.
- knowledge/main/about/: Agent self-knowledge files. Not user-facing docs - written for the agent's internal reference.
- webui/components/AGENTS.md: DOX contract for Alpine component architecture.
- webui/js/AGENTS.md: DOX contract for frontend infrastructure, modal stack, API helpers, and extension loading.
- plugins/AGENTS.md: DOX contract for bundled and custom plugin architecture; `usr/plugins/` remains ignored user state.

---

## Development Patterns & Conventions

### Backend (Python)
- Context Access: Use from agent import AgentContext, AgentContextType (not helpers.context).
- Communication: Use mq from helpers.messages to log proactive UI messages:
  mq.log_user_message(context.id, "Message", source="Plugin")
- API Handlers: Derive from ApiHandler in helpers/api.py.
- Extensions: Use the extension framework in helpers/extension.py for lifecycle hooks.
- Error Handling: Use RepairableException for errors the LLM might be able to fix.

### Frontend (Alpine.js)
- Store Gating: Always wrap store-dependent content in a template:
```html
<div x-data>
  <template x-if="$store.myStore">
    <div x-init="$store.myStore.onOpen()">...</div>
  </template>
</div>
```
- Store Registration: Use createStore from /js/AlpineStore.js.
- Template Expression Scope: Keep Alpine attributes declarative: property reads, bindings, guards, and short method calls. Put object or array construction, cloning, multi-step mutation, async workflows, and reusable behavior in named JavaScript store or component methods; simple toggles and assignments may stay inline.
- Modals: Use openModal(path) and closeModal() from /js/modals.js.

### Plugin Architecture
- Location: Always develop new plugins in usr/plugins/.
- Manifest: Every plugin requires a plugin.yaml with name, description, version, and optionally settings_sections, per_project_config, per_agent_config, and always_enabled.
- Discovery: Conventions based on folder names (api/, tools/, webui/, extensions/).
- Plugin-local Python imports: Prefer `usr.plugins.<plugin_name>...` for code that lives under `usr/plugins/`. Avoid `sys.path` hacks and avoid symlink-dependent `plugins.<plugin_name>...` imports for community plugins.
- Runtime hooks: Plugins may also expose hooks in hooks.py, callable by the framework through helpers.plugins.call_plugin_hook(...).
- Hook runtime: hooks.py executes inside the Agent Zero framework Python environment, so sys.executable -m pip installs dependencies into that same framework runtime.
- Environment targeting: If a plugin needs packages or binaries for the separate agent execution runtime or system environment, it must explicitly switch environments in a subprocess by targeting the correct interpreter, virtualenv, or package manager.
- Settings: Use get_plugin_config(plugin_name, agent=agent) to retrieve settings. Plugins can expose a UI for settings via webui/config.html. Plugin settings modals instantiate a local context from $store.pluginSettingsPrototype; bind plugin fields to config.* and use context.* for modal-level state and actions.
- Activation: Global and scoped activation rules are stored as .toggle-1 (ON) and .toggle-0 (OFF). Scoped rules are handled via the plugin "Switch" modal.
- Cleanup rule: Plugins should not permanently modify the system in ways that outlive the plugin. Deleting a plugin should not leave behind symlinks, unmanaged services, or stray files outside plugin-owned paths unless the user explicitly requested that behavior.

### Releases
- Docker publishing automation lives in `.github/workflows/docker-publish.yml`.
- Releasable tags follow `v{X}.{Y}` and only tags `>= v1.0` are considered by the workflow.
- The latest eligible tag on `main` also creates or updates a GitHub release after the Docker image push succeeds.
- GitHub release notes are generated on the fly in `.github/scripts/docker_release_plan.py` by comparing the new tag against the previous published GitHub release tag, collecting commit subjects and descriptions in that range, and sending them to OpenRouter.
- The OpenRouter call uses `OPENROUTER_API_KEY` and `OPENROUTER_MODEL_NAME` from the workflow environment, with the system prompt stored in `scripts/openrouter_release_notes_system_prompt.md`.
- Prioritize user-visible features, important fixes, infra or packaging changes, and breaking notes. Skip low-signal churn.
- If the generated summary has no meaningful content, the release body falls back to `No release notes.`

### Lifecycle Synchronization
| Action | Backend Extension | Frontend Lifecycle |
|---|---|---|
| Initialization | agent_init | init() in Store |
| Mounting | N/A | x-create directive |
| Processing | monologue_start/end | UI loading state |
| Cleanup | context_deleted | x-destroy directive |

---

## Safety and Permissions

### Allowed Without Asking
- Read any file in the repository.
- Update code files in usr/.

### Ask Before Executing
- pip install (new dependencies).
- Deleting core files outside of usr/ or tmp/.
- Modifying agent.py or initialize.py.
- Making git commits or pushes.

### Never Do
- Commit, hardcode or leak secrets or .env files.
- Bypass CSRF or authentication checks.
- Hardcode API keys.

---

## Code Examples

### API Handler (Good)
```python
from helpers.api import ApiHandler, Request, Response

class MyHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        # Business logic here
        return {"ok": True, "data": "result"}
```

### Alpine Store (Good)
```javascript
import { createStore } from "/js/AlpineStore.js";

export const store = createStore("myStore", {
    items: [],
    init() { /* global setup */ },
    onOpen() { /* mount setup */ },
    cleanup() { /* unmount cleanup */ }
});
```

### Tool Definition (Good)
```python
from helpers.tool import Tool, Response

class MyTool(Tool):
    async def execute(self, **kwargs):
        # Tool logic
        return Response(message="Success", break_loop=False)
```

---

## Git Workflow

- Docker publish automation lives in `.github/workflows/docker-publish.yml`.
- Release tags handled by automation must match `vX.Y` and be `>= v1.0`.
- Allowed release branches are configured at the top of the workflow. `main` publishes `<tag>` and `latest`; other allowed branches publish only the branch tag.
- Manual dispatch accepts an optional tag. Without a tag it backfills missing Docker Hub tags. With a tag it rebuilds that exact target and only refreshes `latest` and the GitHub release when that tag is still the newest eligible tag on `main`.

---

## Release Notes

- The latest eligible `main` tag generates its GitHub release notes during Docker publish instead of reading committed Markdown files.
- The release-note prompt is editable in `scripts/openrouter_release_notes_system_prompt.md`.
- The commit range starts at the previous published GitHub release tag, not merely the previous semantic tag in the repository.

## Troubleshooting

### Dependency Conflicts
If pip install fails, try running in a clean virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### WebSocket Connection Failures
- Check if X-CSRF-Token is being sent.
- Ensure the runtime ID in the session matches the current server instance.

---

*Last updated: 2026-06-01*
*Maintained by: Agent Zero Core Team*


# DOX framework

- DOX is highly performant AGENTS.md hierarchy installed here
- Agent must follow DOX instructions across any edits

## Core Contract

- AGENTS.md files are binding work contracts for their subtrees
- Work products, source materials, instructions, records, assets, and durable docs must stay understandable from the nearest applicable AGENTS.md plus every parent AGENTS.md above it

## Read Before Editing

1. Read the root AGENTS.md
2. Identify every file or folder you expect to touch
3. Walk from the repository root to each target path
4. Read every AGENTS.md found along each route
5. If a parent AGENTS.md lists a child AGENTS.md whose scope contains the path, read that child and continue from there
6. Use the nearest AGENTS.md as the local contract and parent docs for repo-wide rules
7. If docs conflict, the closer doc controls local work details, but no child doc may weaken DOX

Do not rely on prior context. Re-read the applicable DOX chain in the current session before editing.

## Update After Editing

Every meaningful change requires a DOX pass before the task is done.

Update the closest owning AGENTS.md when a change affects:

- purpose, scope, ownership, or responsibilities
- durable structure, contracts, workflows, or operating rules
- required inputs, outputs, permissions, constraints, side effects, or artifacts
- user preferences about behavior, communication, process, organization, or quality
- AGENTS.md creation, deletion, move, rename, or index contents

Update parent docs when parent-level structure, ownership, workflow, or child index changes. Update child docs when parent changes alter local rules. Remove stale or contradictory text immediately. Small edits that do not change behavior or contracts may leave docs unchanged, but the DOX pass still must happen.

Do not create or update DOX docs for changes confined to ignored runtime or user-state folders under `usr/` or `tmp/` unless the user explicitly asks for those folders to be documented.

## Hierarchy

- Root AGENTS.md is the DOX rail: project-wide instructions, global preferences, durable workflow rules, and the top-level Child DOX Index
- Child AGENTS.md files own domain-specific instructions and their own Child DOX Index
- Each parent explains what its direct children cover and what stays owned by the parent
- The closer a doc is to the work, the more specific and practical it must be

## Child Doc Shape

- Create a child AGENTS.md when a folder becomes a durable boundary with its own purpose, rules, responsibilities, workflow, materials, or quality standards
- Work Guidance must reflect the current standards of the project or user instructions; if there are no specific standards or instructions yet, leave it empty
- Verification must reflect an existing check; if no verification framework exists yet, leave it empty and update it when one exists

Default section order:
- Purpose
- Ownership
- Local Contracts
- Work Guidance
- Verification
- Child DOX Index

## Style

- Keep docs concise, current, and operational
- Document stable contracts, not diary entries
- Put broad rules in parent docs and concrete details in child docs
- Prefer direct bullets with explicit names
- Do not duplicate rules across many files unless each scope needs a local version
- Delete stale notes instead of explaining history
- Trim obvious statements, repeated rules, misplaced detail, and warnings for risks that no longer exist

## Closeout

1. Re-check changed paths against the DOX chain
2. Update nearest owning docs and any affected parents or children
3. Refresh every affected Child DOX Index
4. Remove stale or contradictory text
5. Run existing verification when relevant
6. Report any docs intentionally left unchanged and why

## User Preferences

- Do not document changes in `usr/` or `tmp/`; treat both as ignored runtime/user-state folders unless explicitly requested otherwise.

## Child DOX Index

Direct child DOX files:

| Child | Scope |
| --- | --- |
| [.github/AGENTS.md](.github/AGENTS.md) | GitHub Actions workflows and release automation scripts. |
| [agents/AGENTS.md](agents/AGENTS.md) | Bundled agent profiles, profile-local prompts, and profile-local tools. |
| [api/AGENTS.md](api/AGENTS.md) | HTTP API handlers and WebSocket handler entry points. |
| [conf/AGENTS.md](conf/AGENTS.md) | Repository-shipped configuration defaults and templates. |
| [docker/AGENTS.md](docker/AGENTS.md) | Docker build contexts, image definitions, and runtime compose files. |
| [docs/AGENTS.md](docs/AGENTS.md) | Human-facing documentation, developer guides, screenshots, and agent deep dives. |
| [extensions/AGENTS.md](extensions/AGENTS.md) | Core lifecycle extension hook implementations for backend and WebUI surfaces. |
| [helpers/AGENTS.md](helpers/AGENTS.md) | Shared backend framework utilities and cross-cutting runtime services. |
| [knowledge/AGENTS.md](knowledge/AGENTS.md) | Built-in agent self-knowledge and indexed reference material. |
| [lib/AGENTS.md](lib/AGENTS.md) | Lightweight browser-side helper scripts outside the main WebUI bundle. |
| [plugins/AGENTS.md](plugins/AGENTS.md) | Bundled system plugins shipped with the framework. |
| [prompts/AGENTS.md](prompts/AGENTS.md) | Core prompt templates loaded by agents and framework workflows. |
| [scripts/AGENTS.md](scripts/AGENTS.md) | Repository maintenance scripts invoked by automation or maintainers. |
| [skills/AGENTS.md](skills/AGENTS.md) | Bundled Agent Zero skills and their agent-facing instructions. |
| [tests/AGENTS.md](tests/AGENTS.md) | Pytest regression and contract tests. |
| [tools/AGENTS.md](tools/AGENTS.md) | Core agent tool implementations. |
| [webui/AGENTS.md](webui/AGENTS.md) | Flask-served Alpine.js WebUI shell, frontend modules, components, CSS, assets, and vendor libraries. |

Intentionally unindexed local or generated roots:

| Path | Reason |
| --- | --- |
| `.conda/`, `.venv/` | Local Python environments. |
| `.pytest_cache/`, `__pycache__/` | Generated test and bytecode caches. |
| `.vscode/`, `.windsurf/` | Editor-local configuration and assistant metadata. |
| `logs/` | Runtime output. |
| `tmp/` | Ignored runtime caches, uploads, and generated working files; do not document changes here unless explicitly requested. |
| `usr/` | Ignored local user data, settings, plugins, uploads, chats, and workdirs; do not document changes here unless explicitly requested. |
| `python/` | Generated or legacy runtime cache mirror; current source lives in root-level `api/`, `helpers/`, `tools/`, and `extensions/`. |
