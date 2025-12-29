# Agent Zero Documentation Audit Report

_Date: 2025-12-26_

This audit was completed before documentation updates. It inventories outdated content, gaps, and necessary corrections based on the community knowledge extraction (Sep–Dec 2025) and the current `/docs` content.

## Sources Consulted
- `/docs/*.md` and `/docs/designs/*.md`
- Community Knowledge Extraction (Sep–Dec 2025)

## Cross-Cutting Findings (High Priority)
- **Model naming by provider is inconsistent**: several docs still imply `openai/` prefixes for native OpenAI, which is only correct for OpenRouter.
- **Prompt customization paths are outdated**: docs reference `/prompts` overrides; current guidance is per-agent prompts under `/a0/agents/<agent_name>/` (post v0.9.7).
- **Docker persistence advice is risky**: mapping the entire `/a0` directory is discouraged; Backup & Restore is the recommended path for upgrades.
- **Browser agent reliability**: browser agent is currently problematic; MCP-based browser tools should be recommended.
- **Projects/Tasks/MCP/A2A coverage is incomplete**: features exist but are not documented consistently or with practical guidance.
- **Secrets and backups**: secrets are stored in `/a0/tmp/secrets.env` and are not always preserved by backups; this is not clearly documented.

## File-by-File Audit Summary

### `docs/README.md`
- **Outdated/Incorrect**: missing several docs in the hub; TOC link typo (`archicture.md`).
- **Gaps**: no links to MCP setup, notifications, tunnel, quickstart, designs, or audit report.
- **Planned Action**: update TOC, fix broken link, add missing navigation links.

### `docs/installation.md`
- **Outdated/Incorrect**:
  - References separate “Hacking Edition” image; now included as a profile in the main image.
  - Suggests mapping full `/a0` (even as “not recommended”); current guidance is to avoid it.
  - “Prompts Subdirectory” field no longer matches current UI (agent profile-based prompts).
- **Gaps**:
  - Port mapping guidance (at least one host port mapped to container port 80).
  - Model naming rules by provider, context window split guidance, utility model sizing.
  - Update workflow via Backup & Restore.
- **Planned Action**: replace outdated sections, add precise model/provider notes, update Docker and update workflow guidance.
- **Removal Reasoning**: remove references to `agent0ai/agent-zero:hacking` and mapping full `/a0` because they are no longer recommended or accurate.

### `docs/usage.md`
- **Outdated/Incorrect**: missing explicit section heading for “Mathematical Expressions.”
- **Gaps**:
  - No coverage of Projects, Tasks/Scheduling, Secrets usage, or browser agent status and MCP alternatives.
  - No mention of chat history location (`/a0/tmp/chats/`).
- **Planned Action**: add missing sections and cross-links; document browser agent caveats and MCP recommendations.

### `docs/architecture.md`
- **Outdated/Incorrect**:
  - Prompt customization still points to `/prompts` overrides instead of agent profile paths.
- **Gaps**:
  - Memory management best practices, embedding model details, instruments vs tools distinction.
- **Planned Action**: update prompt paths, add memory and instrument clarifications, link to usage/extensibility.

### `docs/extensibility.md`
- **Outdated/Incorrect**: prompt override guidance references old layout for some workflows.
- **Gaps**: instruments vs tools, projects context separation and project-specific agents are underexplained.
- **Planned Action**: refine prompt override guidance, expand projects guidance, add instruments vs tools section.

### `docs/connectivity.md`
- **Gaps**:
  - A2A lacks practical guidance and examples.
  - No explicit cross-link between MCP server (A0 as server) and MCP client setup.
- **Planned Action**: add A2A usage notes and cross-links.

### `docs/mcp_setup.md`
- **Gaps**:
  - No curated MCP recommendations (Browser OS, Playwright, Chrome DevTools).
  - No n8n integration mention.
  - Insufficient guidance for connecting to host MCP servers from Docker.
- **Planned Action**: add practical MCP server recommendations, docker networking notes, and cross-links.

### `docs/troubleshooting.md`
- **Gaps**:
  - Missing guidance on model ID errors by provider, OpenAI API vs Plus, secrets backup, and browser agent issues.
  - Lacks updated notes on context window tuning and utility model sizing.
- **Planned Action**: add targeted troubleshooting entries with links to relevant docs.

### `docs/quickstart.md`
- **Gaps**: no clarification that Docker is the recommended runtime; local `run_ui.py` is dev-focused.
- **Planned Action**: add a short note and link to installation.

### `docs/tunnel.md`
- **Status**: mostly accurate; keep but cross-link from installation/usage where relevant.

### `docs/notifications.md`
- **Status**: accurate; cross-link from tasks/scheduling content where it is referenced.

### `docs/designs/*`
- **Status**: design specs appear accurate; no updates required for this task.

## Removal Log (Planned)
- **Hacking Edition Docker image reference** → remove because hacker profile is now included in the main image.
- **Guidance to map full `/a0`** → remove because it causes upgrade issues; Backup & Restore is recommended.
- **Prompt subdirectory customization via `/prompts`** → replace with per-agent prompt overrides at `/a0/agents/<agent_name>/prompts`.

---

This audit report is intended to guide the documentation edits that follow.
