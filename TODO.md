# TODO Roadmap — Frontend Components (Phase 1, Non-settings)

Source of truth: `COMPONENTS.md`
Scope: Extract UI from `index.html` into modular components without changing Settings. Settings migration is deferred and must be coordinated with the project lead.

## Tasks (Cursor TODO list)

1) Create Preferences component and store [completed]
- UI: `components/preferences/preferences-panel.html`
- Store: `components/preferences/preferences-store.js`
- Includes: Autoscroll, Dark Mode, Speech, Show Thoughts, Show JSON, Show Utility Messages
- Acceptance: Toggles parity; persistent state (localStorage) as today; no `safeCall` reliance

2) Extract Quick Actions toolbar to component [completed]
- UI: `components/chat/quick-actions.html`
- Actions: Reset Chat, New Chat, Load Chat, Save Chat, Restart, Open Settings

3) Extract Chats list sidebar to component and store [pending]
- UI: `components/chat/sidebar/chats.html`
- Store: `components/chat/sidebar/chats-store.js`
- Includes: list/select/kill chats, highlight selected

4) Extract Tasks list sidebar to component and store [pending]
- UI: `components/chat/sidebar/tasks.html`
- Store: `components/chat/sidebar/tasks-store.js`
- Includes: list tasks, open detail, reset task chat, delete

5) Extract File Browser modal to component and store [pending]
- UI: `components/file-browser/file-browser.html`
- Store: `components/file-browser/file-browser-store.js`
- Parity with current `#fileBrowserModal` and `file_browser.js`

6) Extract Generic viewer modal to component [pending]
- UI: `components/generic-modal/viewer.html`
- Replace legacy `#genericModal` viewer

7) Extract Full-screen input modal to component and store [pending]
- UI: `components/chat/input/full-screen-input.html`
- Store: `components/chat/input/full-screen-store.js`
- Parity: undo/redo, wrap toggle, Ctrl+Enter close

8) Extract Progress bar and Stop Speech to component [pending]
- UI: `components/chat/status/progress.html`
- Integrate visibility with `$store.speech`

9) Extract Bottom action bar to component [pending]
- UI: `components/chat/input/bottom-actions.html`
- Includes: Import knowledge, Files, History, Context, Nudge

10) Extract Time-date and connection status header to component [pending]
- UI: `components/chat/header/status-bar.html`
- Keep notifications icon component as-is

11) Normalize preference toggles into Alpine store (remove `safeCall`) [completed]
- Consolidate side-effects into the preferences store

Recommended implementation order:
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11

Out of scope (Deferred — Settings):
- Componentize Scheduler settings tab into `settings/scheduler` with store [deferred]
- Factor Settings sections into dedicated components per area [deferred]

---

## How to recreate this TODO list in a fresh Cursor chat

Ask the assistant to create the same TODO list using the following tool payload. This must be the first action after attaching `COMPONENTS.md` and `TODO.md`.

```json
{
  "merge": false,
  "todos": [
    {"content": "Create Preferences component and store", "status": "pending", "id": "todo-prefs-component"},
    {"content": "Extract Quick Actions toolbar to component", "status": "pending", "id": "todo-toolbar-quick"},
    {"content": "Extract Chats list sidebar to component and store", "status": "pending", "id": "todo-sidebar-chats"},
    {"content": "Extract Tasks list sidebar to component and store", "status": "pending", "id": "todo-sidebar-tasks"},
    {"content": "Extract File Browser modal to component and store", "status": "pending", "id": "todo-file-browser-modal"},
    {"content": "Extract Generic viewer modal to component", "status": "pending", "id": "todo-generic-modal"},
    {"content": "Extract Full-screen input modal to component and store", "status": "pending", "id": "todo-fullscreen-input-modal"},
    {"content": "Extract Progress bar and Stop Speech to component", "status": "pending", "id": "todo-progress-speech"},
    {"content": "Extract Bottom action bar to component", "status": "pending", "id": "todo-bottom-actions"},
    {"content": "Extract Time-date and connection status header to component", "status": "pending", "id": "todo-time-status-header"},
    {"content": "Normalize preference toggles into Alpine store (remove safeCall)", "status": "pending", "id": "todo-prefs-store-normalize"}
  ]
}
```

After creating TODOs:
- Set the first task (Preferences component and store) to `in_progress` and begin implementation following `COMPONENTS.md`.
- Do not modify anything under `webui/components/settings/*` without explicit approval.

## Notes for implementers
- Replace `index.html` segments with `<x-component path="...">` entries when migrating.
- Use `createStore()` from `webui/js/AlpineStore.js` with an `init()` method for side-effects.
- Preserve CSS initially (lift-and-shift), then refactor styles later if needed.
