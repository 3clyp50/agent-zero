# Documentation Audit Report

Date: 2025-09-26
Source of truth: `community-extraction.md` (Discord knowledge extraction, Sep–Dec 2025)

This report captures the pre-edit audit of the `/docs` tree. It enumerates outdated areas, gaps, and removals with reasoning. The report is intentionally concise but structured so future updates can trace *why* sections changed.

## Summary of Global Issues
- **Docker guidance** needs to emphasize port mapping to container port 80, the Backup & Restore update workflow, and avoiding full `/a0` volume mapping.
- **Model configuration** is missing provider-specific naming rules, context window sizing guidance, and utility model sizing guidance (70B+ for reliable memory extraction).
- **Prompt customization** references legacy `/prompts` subdir settings that no longer exist; custom prompts are now agent-profile scoped under `/a0/agents/<profile>/`.
- **Browser agent** guidance omits current instability and recommended MCP alternatives.
- **Projects + Tasks** features need clearer explanations (context separation, project-scoped memory/instructions, scheduling + notifications).
- **MCP** should document both *client* and *server* directions and mention common MCP servers used in the community.
- **Secrets** handling needs explicit guidance (use secrets aliases in prompts; secrets file location; OpenAI API vs Plus clarification).

## File-by-File Audit

### `docs/README.md`
- **Outdated/Incorrect**: Missing links for `mcp_setup.md`, `notifications.md`, `tunnel.md`, `quickstart.md`, and design specs. Typo in `archicture.md` link.
- **Gaps**: No navigation references to Projects/Tasks or MCP setup.
- **Action**: Update TOC and fix broken link.

### `docs/installation.md`
- **Outdated/Incorrect**:
  - Hacker edition referenced as separate image; now included as a profile in the main image.
  - Prompts subdirectory setting no longer exists.
  - Volume mapping guidance still allows mapping `/a0`.
- **Gaps**:
  - Port mapping best practice (map host → container `80`, `0:80` for random).
  - Model provider naming rules (remove `openai/` when using OpenAI directly).
  - Context window sizing guidance and utility model sizing guidance (70B+ recommended for reliable memory extraction).
  - Update workflow: Backup & Restore in Settings UI.
- **Removals (with reason)**:
  - Remove instructions that suggest mapping the entire `/a0` directory because it conflicts with upgrade guidance and is explicitly discouraged by maintainers.

### `docs/usage.md`
- **Outdated/Incorrect**:
  - Tool example references `document_query_tool` (tool name is `document_query`).
- **Gaps**:
  - Projects feature usage patterns and context separation.
  - Tasks & scheduling flow, including scheduler UI and notifications.
  - Browser agent reliability status + MCP alternatives (Browser OS, Chrome DevTools, Playwright).
  - Chat history location (`/a0/tmp/chats/`).

### `docs/architecture.md`
- **Outdated/Incorrect**:
  - Prompts section assumes `prompts_subdir` and `prompts/` overrides.
  - Storage/persistence language implies `/a0` is safe to mount wholesale.
- **Gaps**:
  - Memory embedding model is local + small (100MB) and has footprint implications.
  - Distillation/memorize patterns and context window heuristics.
  - Tools vs Instruments distinction (and how instruments are stored in `/a0/instruments/custom`).
- **Removals (with reason)**:
  - Remove references to `prompts_subdir` since it no longer exists in Settings.

### `docs/extensibility.md`
- **Outdated/Incorrect**:
  - Prompts override location and structure are legacy.
- **Gaps**:
  - Project-scoped instructions/knowledge layout.
  - Instruments definition (difference vs tools).
  - Hacker profile selection guidance.

### `docs/connectivity.md`
- **Gaps**:
  - Needs practical A2A usage notes and cross-links to Projects (context separation alternatives).
  - MCP server section should mention where to find URLs and tokens in Settings, plus a “client vs server” distinction.

### `docs/mcp_setup.md`
- **Gaps**:
  - Should mention MCP use cases (browser automation alternatives), and common community MCPs (Browser OS, Chrome DevTools, Playwright).
  - Should link to connectivity doc for MCP server mode.

### `docs/quickstart.md`
- **Outdated/Incorrect**: Uses `run_ui.py`/conda flow as default; Docker is now primary.
- **Action**: Update to Docker-first quickstart and point developers to `development.md` if running locally.
- **Removals (with reason)**:
  - Remove conda/run_ui instructions because they describe a legacy setup path and conflict with Docker-first guidance.

### `docs/troubleshooting.md`
- **Gaps**:
  - Invalid model ID causes (provider prefix mismatch).
  - Context window sizing issues, temperature parameter errors.
  - Browser agent dependency issues → MCP alternatives.
  - Secrets lost during backup (copy `/a0/tmp/secrets.env`).
  - UI response length behavior (large outputs stored as files).

### `docs/notifications.md`
- **Gaps**:
  - Cross-link to Tasks scheduling; clarify notifications as part of task automation patterns.

### `docs/tunnel.md`
- **No critical issues** identified, but should be cross-linked from installation or usage for remote access.

### `docs/designs/*`
- **No updates** needed; these are specification archives. Only ensure they’re linked from the main README for discoverability.
