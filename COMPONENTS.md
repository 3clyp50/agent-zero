# Frontend Component Architecture

## Introduction

This document outlines the transition of Agent Zero's frontend architecture from a monolithic `index.html` file to a modular, component-based structure. The goal is to improve code maintainability, scalability, and readability, facilitating the integration of new features and the management of framework settings.

## Component Directory Structure

The `webui/components/` directory is currently organized by feature, grouping related HTML components and their JavaScript stores. This modular approach makes it easier to manage and develop specific parts of the application. The current structure is as follows:

1.  **`chat/`**: Contains components that are part of the main chat interface. This includes complex features that have their own state and logic.
    *   `attachments/`: Manages file attachments, including a drag-and-drop overlay, an image modal viewer, the input preview, and a dedicated `attachmentsStore.js` for state management.
    *   `speech/`: Houses the `speech-store.js` which controls the Speech-to-Text (STT) and Text-to-Speech (TTS) functionalities.

2.  **`messages/`**: Holds components designed to enhance or interact with individual chat messages.
    *   `action-buttons/`: Provides the contextual buttons (e.g., copy, speak) that appear on message hover.
    *   `resize/`: Contains the `message-resize-store.js` responsible for managing the expanded/collapsed state of messages.

3.  **`notifications/`**: A self-contained module for the entire notification system.
    *   It includes UI components for the notification icon (`notification-icons.html`), the modal window (`notification-modal.html`), and the toast alerts (`notification-toast-stack.html`).
    *   The core logic and state are managed by `notification-store.js`.

4.  **`settings/`**: This directory is dedicated to the components that make up the settings modal. Each subdirectory corresponds to a specific settings panel, demonstrating a clear organizational pattern for future additions.
    *   Examples include `backup/`, `mcp/`, `speech/`, and `tunnel/`, each containing their respective components and stores.
    *   This is the target location for settings currently hardcoded in `index.html`.

5.  **`_examples/`**: A resource for developers.
    *   It contains boilerplate code (`_example-component.html`, `_example-store.js`) that serves as a template for creating new components and stores, ensuring consistency and adherence to the established architecture.

## Component Engine (supporting files in `webui/js/`)

- **`components.js`**: Loader for custom `<x-component>` tags. Fetches HTML, injects styles/scripts, resolves nested modules, maintains a cache, and observes DOM mutations to auto-load components.
- **`AlpineStore.js`**: Thin wrapper around `Alpine.store()` providing `createStore(name, model)` and a proxy so stores are usable before Alpine initializes.
- **`initFw.js`**: Ensures framework initialization order so components and stores are available before Alpine mounts, preventing race conditions.
- **`modals.js`**: Centralized modal open/close helpers used by multiple components (e.g., notifications, image viewer, generic viewer).

## Roadmap — Phase 1 (Non-settings refactor)

Objective: Extract UI currently embedded in `index.html` into modular components (no changes to the Settings modal or `webui/components/settings/*`).

Planned components and stores (proposed paths):

1.  Preferences Panel (left sidebar)
    - UI: `components/preferences/preferences-panel.html`
    - Store: `components/preferences/preferences-store.js`
    - Scope: Autoscroll, Dark Mode, Speech, Show Thoughts, Show JSON, Show Utility Messages
    - Acceptance: Toggles update UI instantly; state persisted (localStorage) as today; no reliance on `safeCall`.
    - Status: Completed — `<x-component path="preferences/preferences-panel.html">` wired in `index.html`; store created; removed `safeCall`.

2.  Quick Actions Toolbar (left sidebar top)
    - UI: `components/chat/quick-actions.html`
    - Scope: Reset Chat, New Chat, Load Chat, Save Chat, Restart, Open Settings
    - Acceptance: Button actions call existing functions; keyboard focus management preserved.
    - Status: Completed — `<x-component path="chat/quick-actions.html">` wired in `index.html`; behavior unchanged.

3.  Sidebar — Chats List
    - UI: `components/chat/sidebar/chats.html`
    - Store: `components/chat/sidebar/chats-store.js`
    - Scope: List, select, kill chats; highlight selected
    - Acceptance: Parity with current behavior and performance on large lists.

4.  Sidebar — Tasks List
    - UI: `components/chat/sidebar/tasks.html`
    - Store: `components/chat/sidebar/tasks-store.js`
    - Scope: List tasks, open detail, reset chat for task, delete
    - Acceptance: Matches existing actions and badges.

5.  File Browser Modal
    - UI: `components/file-browser/file-browser.html`
    - Store: `components/file-browser/file-browser-store.js`
    - Scope: Navigate, sort, download, delete, upload; preserves current UX
    - Acceptance: Feature parity with `#fileBrowserModal` and `file_browser.js`.

6.  Generic Viewer Modal (HTML viewer)
    - UI: `components/generic-modal/viewer.html`
    - Scope: Replace `#genericModal` content with componentized version
    - Acceptance: Same rendering and keyboard behavior.

7.  Full-screen Input Modal
    - UI: `components/chat/input/full-screen-input.html`
    - Store: `components/chat/input/full-screen-store.js`
    - Scope: Text history, undo/redo, wrap toggle, close on Ctrl+Enter
    - Acceptance: Matches current toolbar features and shortcuts.

8.  Progress Bar + Stop Speech Area
    - UI: `components/chat/status/progress.html`
    - Scope: Render streaming progress; integrate Stop Speech visibility with `$store.speech`
    - Acceptance: Same DOM hooks used by `messages.js` (no regressions).

9.  Bottom Action Bar (below input)
    - UI: `components/chat/input/bottom-actions.html`
    - Scope: Import knowledge, Files (open file browser), History, Context, Nudge
    - Acceptance: Triggers existing global actions; tooltips preserved.

10. Header — Time/Date + Connection Status
    - UI: `components/chat/header/status-bar.html`
    - Scope: Time/date update loop; connection indicator; keep notifications icon component as-is
    - Acceptance: Same update cadence and visual parity.

Implementation order (suggested):

1) Preferences Panel → 2) Quick Actions → 3) Sidebar Chats → 4) Sidebar Tasks → 5) File Browser Modal → 6) Generic Viewer Modal → 7) Full-screen Input → 8) Progress + Stop Speech → 9) Bottom Action Bar → 10) Header Status Bar.

Migration protocol:
- For each component:
  - Isolate HTML from `index.html` into `components/*/*.html`.
  - Create store (if needed) via `createStore()` with `init()` hook.
  - Replace original markup with `<x-component path="...">`.
  - Verify lifecycle: component loads before Alpine; stores accessible via `$store`.
  - Keep CSS unchanged initially (lift-and-shift), refactor later if needed.

Out of scope for Phase 1:
- Any changes to `webui/components/settings/*` or the Settings modal behavior.

## Settings Migration (Deferred — coordinate with Jan)

The migration of Settings (including the Scheduler tab within Settings) is intentionally deferred. Before any work on settings, coordinate with the project lead to align frontend and backend changes and define the target structure.

High-level notes (for future coordination only):
- Inventory existing settings in `index.html` and Settings modal.
- Decide settings boundaries between modal vs. sidebar preferences.
- Define backend surface (APIs, schemas) prior to componentization.

## Alpine.js Best Practices

-   **Code Organization**:
    - Separate concerns by keeping HTML, JavaScript, and CSS distinct.
    - Use functions that return objects to define component data, improving maintainability. ([Source](https://alpinedevtools.com/blog/stores-usage-guide))

-   **State Management**:
    - Use Alpine.js stores to manage global and shared state between components.
    - Avoid overloading `x-data` with too much data or too many methods. ([Source](https://alpinedevtools.com/blog/stores-usage-guide))

-   **Component Communication**:
    - Use custom events and the `x-on` attribute for communication between components.
    - Consider using libraries like Spruce for global state management if necessary. ([Source](https://wittyprogramming.net/articles/cross-component-communication-pattern-in-alpinejs/))

-   **Performance**:
    - Avoid excessive use of utility classes; prefer custom CSS for complex styles.
    - Use lazy loading to load resources only when necessary, reducing initial load time. ([Source](https://codezup.com/crafting-modern-ui-components-with-tailwind-css-and-alpine-js/))

## Conclusion

By adopting a component-based architecture and following Alpine.js best practices, we will significantly improve the structure and maintainability of the Agent Zero frontend. This approach will facilitate the integration of new features, the management of settings, and collaboration within the team.
