# Plugins DOX

## Purpose

- Own bundled system plugins shipped with Agent Zero.
- Provide the tracked plugin architecture contract for both bundled plugins and custom plugins developed under ignored `usr/plugins/`.
- Keep plugin behavior discoverable, reversible, and compatible across bundled and custom roots without creating DOX files inside `usr/`.

## Ownership

- Each direct `_plugin_name/` directory owns its `plugin.yaml`, optional `default_config.yaml`, `hooks.py`, API handlers, helpers, tools, prompts, skills, extensions, WebUI assets, and README.
- Plugins may also own `execute.py`, `conf/model_providers.yaml`, plugin-distributed `agents/<profile>/agent.yaml`, static assets, and plugin-local docs.
- `README.md` owns the high-level core plugin architecture summary and community Plugin Index guidance.
- Custom or experimental user plugins belong under `usr/plugins/`, not here, but this file remains their tracked DOX contract.
- Do not create `AGENTS.md` files under `usr/plugins/` unless the user explicitly asks for ignored user-state documentation.

## Local Contracts

- Every plugin directory must include a valid `plugin.yaml`.
- Runtime manifest fields include `name`, `title`, `description`, `version`, `settings_sections`, `per_project_config`, `per_agent_config`, and `always_enabled`.
- Core plugins may use `plugins.<plugin_name>...` imports when they are shipped from this tree.
- User plugins under `usr/plugins/` must use `usr.plugins.<plugin_name>...` imports and avoid `sys.path` hacks or persistent symlink-based imports.
- Plugin extension layouts must use `extensions/python/<point>/`, `extensions/python/_functions/<module>/<qualname>/<start|end>/`, and `extensions/webui/<point>/`.
- The `_functions` extension layout preserves every module and nested qualname segment; do not use retired flattened extension folder names.
- Plugin settings defaults belong in `default_config.yaml`; runtime user settings belong under `usr/`.
- Plugin settings resolution order is project/profile, project, user/profile, user plugin config, then bundled `default_config.yaml`.
- `webui/config.html` settings UIs must bind plugin values to `config.*` and modal state/actions to `context.*` through `$store.pluginSettingsPrototype`.
- Plugin model provider overrides belong in plugin `conf/model_providers.yaml` and merge after base `conf/model_providers.yaml`.
- Global and scoped activation are independent and use `.toggle-1` and `.toggle-0`; `always_enabled: true` forces ON and disables UI toggles.
- `hooks.py` runs in the framework runtime. Explicitly target another runtime if a plugin must prepare the agent execution environment.
- `execute.py` is manual user-triggered setup, maintenance, repair, migration, or refresh work; automatic framework behavior belongs in hooks or lifecycle extensions.
- Plugin routes are `GET /plugins/<name>/<path>`, `POST /api/plugins/<name>/<handler>`, and `POST /api/plugins` for management actions.
- Frontend plugin HTML extensions live under `extensions/webui/<point>/`, include a root Alpine scope, and use `x-move-*` directives when targeting static breakpoints.
- Frontend plugin JS extensions live under `extensions/webui/<point>/` and export a default function.
- Plugin UI must use the A0 notification system for errors, warnings, success, and info instead of inline success/error boxes.
- Banners and discovery cards are provided through Python `banners` extensions by appending dictionaries with unique `id`, `type`, `priority`, and display fields to the `banners` list.
- Alert banner types are `info`, `warning`, and `error`; discovery card types are `hero` and `feature`.
- Banner/card fields may include `title`, `html`, `description`, `thumbnail`, `icon`, `cta_text`, `cta_action`, and `dismissible` depending on type.
- Community discovery cards should use `type: "feature"`; reserve `hero` cards for core system features.
- Supported discovery CTA actions are `open-plugin-config:<plugin_folder_name>`, `open-plugin-hub`, and `open-url:<url>`.
- Plugin deletion or disablement should not leave unmanaged services, symlinks, or files outside plugin-owned paths unless explicitly documented with cleanup.

## Work Guidance

- Prefer plugin-local helpers for behavior used only by one plugin.
- Use shared `helpers/` only for reusable framework behavior.
- Use the notification system for plugin UI feedback.
- Keep plugin README and docs current when user-visible plugin behavior changes.
- Check configuration before injecting setup or discovery banners so configured plugins do not keep advertising setup.
- Use highly unique banner IDs prefixed by plugin name.
- When preparing community plugins, keep plugin contents at the standalone repository root with `plugin.yaml`, `README.md`, and a root `LICENSE`.
- Plugin Index submissions use a separate `index.yaml` under `a0-plugins/plugins/<name>/`; do not confuse it with runtime `plugin.yaml`.

## Verification

- Run plugin-specific tests after changing a bundled plugin.
- Run framework tests for touched extension points, API handlers, tools, settings, or WebUI surfaces.
- For plugins with external services or browser/desktop integrations, perform a targeted smoke check when practical.
- For banner/discovery changes, verify the Welcome Screen renders alert banners, feature cards, dismiss behavior, priority ordering, and CTA behavior.

## Child DOX Index

Direct child DOX files:

| Child | Scope |
| --- | --- |
| [_browser/AGENTS.md](_browser/AGENTS.md) | Built-in Browser plugin: agent browser tool, CDP/headless Chromium runtime, Browser Canvas/modal viewer, settings, host-browser bridge, and Browser skills. |
