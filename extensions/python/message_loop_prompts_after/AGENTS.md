# Message Loop Prompts After Extensions DOX

## Purpose

- Own prompt protocol and extras appended around primary message-loop prompt construction.

## Ownership

- Ordered Python files own current datetime, skill recall/load context, agent info, parallel job status, and workdir extras injection.
- Explicitly loaded skill bodies belong in tool-result history with metadata so they can survive persistence and be reattached after compaction.
- Explicitly loaded skill IDs are chat-wide context data, not agent-local state.
- Legacy active-skill prompt protocol injection must stay empty; selected skills are loaded through history.

## Local Contracts

- Keep injected content bounded and clearly attributed.
- Preserve ordering where later prompt extras depend on earlier recall or load results.
- Do not expose secrets or private files from workdir extras.

## Work Guidance

- Coordinate prompt protocol, history-reattachment, and prompt-extra changes with skill, workdir, and profile contracts.

## Verification

- Inspect rendered prompt protocol/history/extras or run prompt-construction tests after changes.

## Child DOX Index

No child DOX files.
