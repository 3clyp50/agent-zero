# Documentation Audit Report (Pre-Update)

This audit captures issues discovered before any edits. It is structured per documentation file and lists outdated content, gaps, and removals with reasons.

> [!IMPORTANT]
> This report was produced **before** any documentation edits. Use it as a rationale ledger for removals and updates.

## docs/README.md
**Outdated / Incorrect**
- Table of contents is missing several docs (Quickstart, MCP setup, Notifications, Tunnel).
- Broken anchor: `archicture.md#messages-history-and-summarization` (typo in filename).

**Gaps**
- No explicit links to MCP setup, Notifications, Tunnel, or Quickstart guides.
- No quick navigation to Projects/Tasks/MCP/A2A sections.

**Planned Removals (with reasons)**
- None. Content is mostly accurate but incomplete.

---

## docs/installation.md
**Outdated / Incorrect**
- Hacking edition described as a separate image (`agent0ai/agent-zero:hacking`). Community guidance: hacker profile is included in main image and selected in Settings.
- Prompt customization references `/prompts` subdirectories; post v0.9.7 custom prompts live under `/a0/agents/<agent_name>/` with only overrides.
- Update instructions emphasize volume mapping and manual copying; community guidance recommends Backup & Restore as primary upgrade path.
- Volume mapping section suggests mapping `/a0` is acceptable; community guidance explicitly discourages mapping full `/a0`.

**Gaps**
- Port mapping guidance should emphasize mapping at least one host port to container `80` (host port can be `0`).
- Model naming by provider (OpenAI vs OpenRouter, Venice) is missing.
- Utility model minimum capability guidance (>=70B recommended for memory extraction).
- Context window configuration advice (set total context, then allocate memory share).
- Clarification that OpenAI Plus does not include API credits.

**Planned Removals (with reasons)**
- Remove “map full `/a0` for persistence” guidance because it causes upgrade issues and is discouraged by maintainers.
- Remove hacking image reference because it is no longer accurate; replaced by profile selection in Settings.

---

## docs/usage.md
**Outdated / Incorrect**
- Lacks mention of Tasks scheduler and Projects feature usage patterns.

**Gaps**
- Need to document Tasks + Projects workflow, and notification-driven automation.
- Browser agent limitations and MCP alternatives (Browser OS, Chrome DevTools, Playwright) are missing.
- Chat history location (`/a0/tmp/chats/`) is not mentioned.

**Planned Removals (with reasons)**
- None. Content is accurate but incomplete.

---

## docs/architecture.md
**Outdated / Incorrect**
- Prompt customization points to `/prompts/<subdir>` as the user override location; post v0.9.7 overrides are in `/a0/agents/<agent_name>/`.
- Custom tool prompt location references `/prompts/$FOLDERNAME` without mentioning agent-specific overrides.

**Gaps**
- Clarify instruments vs tools distinction (tools are prompt-injected, instruments are not).
- Mention local embedding model and memory extraction reliance on utility model.

**Planned Removals (with reasons)**
- Remove outdated prompt override instructions referencing `/prompts` subdirectories in favor of agent profile overrides.

---

## docs/extensibility.md
**Outdated / Incorrect**
- Prompts section references `/agents/{agent_profile}/prompts/` as the override location; community guidance indicates overrides live directly under `/a0/agents/<agent_name>/` with only custom files.

**Gaps**
- Instruments need clearer documentation and how they differ from tools.
- Projects section should mention context separation and how Projects + Tasks combine.

**Planned Removals (with reasons)**
- Remove references to prompt overrides via `/prompts` subdirectories.

---

## docs/connectivity.md
**Outdated / Incorrect**
- A2A section lacks practical usage examples and context separation guidance.

**Gaps**
- Add practical A2A examples (e.g., two instances for isolated contexts).
- Clarify MCP server vs MCP client usage in Agent Zero.

**Planned Removals (with reasons)**
- None.

---

## docs/mcp_setup.md
**Outdated / Incorrect**
- MCP client configuration is accurate but missing newly recommended MCP servers and browser alternatives.

**Gaps**
- Add guidance for Browser OS, Chrome DevTools MCP, Playwright MCP.
- Mention n8n and Gmail MCP patterns.
- Mention that browser agent is currently unstable and MCPs are preferred.

**Planned Removals (with reasons)**
- None.

---

## docs/quickstart.md
**Outdated / Incorrect**
- Assumes conda + `python run_ui.py` (legacy host runtime) as the primary path; Docker is now the standard.

**Gaps**
- Add quick Docker-based launch steps and port discovery.

**Planned Removals (with reasons)**
- Remove conda/host-runtime quickstart path to avoid steering users to deprecated setup.

---

## docs/troubleshooting.md
**Outdated / Incorrect**
- Lacks known error resolutions documented by maintainers (invalid model ID, temperature extra parameter).

**Gaps**
- Add model naming pitfalls, context window issues, temperature param errors, secrets backup caveat, and OpenAI API vs Plus clarification.
- Add chat history location and secrets file location for recovery (`/a0/tmp/chats/`, `/a0/tmp/secrets.env`).

**Planned Removals (with reasons)**
- None.

---

## docs/notifications.md, docs/development.md, docs/tunnel.md
**Outdated / Incorrect**
- No critical inaccuracies found.

**Gaps**
- Ensure cross-links from Usage/Tasks/Projects to Notifications where relevant.

**Planned Removals (with reasons)**
- None.
