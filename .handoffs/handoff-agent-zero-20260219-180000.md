# Workflow Handoff: agent-zero

> **Session**: 2026-02-19T18:00:00Z
> **Agent**: Claude (Cursor IDE)
> **Handoff Reason**: checkpoint — plan confirmed, ready to execute

---

## Ξ State Vector

**Objective**: Extend the plugin schema and backend models with our extra fields, fix the broken `python/api/plugins.py` (calls non-existent functions), wire up plugin list UI buttons, fix button styles, and add an info modal.

**Phase**: Plugin List UI + Schema Alignment | Progress: 0% | Status: active (plan confirmed, no edits yet)

**Current Focus**:
`python/helpers/plugins.py` is already Jan's clean canonical version — no old function names remain. The only real backend breakage is `python/api/plugins.py` calling three functions that no longer exist. The plan is in `.cursor/plans/plugin_list_ui_+_schema_alignment_eb81a989.plan.md`.

---

## Δ Context Frame

### Decisions Log
| ID | Decision | Rationale | Reversible |
|----|----------|-----------|------------|
| D1 | Do NOT touch `python/helpers/plugins.py` for cleanup — it's already Jan's clean file | User uploaded Jan's raw version; no old functions remain | n/a |
| D2 | Only add fields to `PluginMetadata`/`PluginListItem` — additive changes only | Preserves Jan's architecture | yes |
| D3 | `config.html` replaces `settings.html` for plugin config screen | Jan's convention: `has_config_screen` detected from `webui/config.html` | no (convention) |
| D4 | `config.json` replaces `settings.json` for plugin config data | Jan renamed `CONFIG_FILE_NAME` | no (convention) |
| D5 | Remove `list` action from `python/api/plugins.py`; Jan's `plugins_list.py` owns listing | Avoids duplicating listing logic | no |
| D6 | Rename API actions `get_settings`/`save_settings` → `get_config`/`save_config` | Match Jan's naming (`get_plugin_config`, `save_plugin_config`) | no |
| D7 | `plugins-subsection.html` switches to `plugins_list` API, filters client-side by `settings_sections` | Reuses Jan's list endpoint; avoids a new server-side filter | yes |
| D8 | Plugin info modal reads `pluginListStore.selectedPlugin` — no separate store | Store already registered; `selectedPlugin` added to `pluginListStore` | yes |
| D9 | `settings_tabs` field → renamed to `settings_sections` | User direction | no (convention) |

### Constraints Active
- **Do not add new functions to `python/helpers/plugins.py`** beyond extending the two Pydantic models and `get_enhanced_plugins_list`
- **Do not use old names**: `get_plugin_settings`, `save_plugin_settings`, `find_plugin_file`, `determine_plugin_save_file_path`, `list_plugins_with_metadata` — none of these exist in Jan's file
- Frontend button styles must match `webui/components/settings/skills/list.html` skill card buttons
- `get_webui_extensions` returns `List[str]` (not `List[Dict]`) — do not regress

### Key Facts About Jan's `plugins.py` (the canonical file)
- Functions: `get_plugin_config`, `save_plugin_config`, `find_plugin_asset`, `determine_plugin_asset_path`
- `find_plugin_asset` only accepts `agent: Agent | None` — no string project/profile params
- `get_enhanced_plugins_list(custom, builtin)` builds `PluginListItem` from `plugin.json`
- `PluginMetadata` currently only has `description: str = ""`
- `PluginListItem` currently has `name`, `path`, `description`, `has_main_screen`, `has_config_screen`

---

## Φ Code Map

### The Only Broken File
| File | Problem |
|------|---------|
| `python/api/plugins.py` | Calls `list_plugins_with_metadata` (gone), `get_plugin_settings` (gone → now `get_plugin_config`), `save_plugin_settings` (gone → now `save_plugin_config`) |

### Files to Edit (8 tasks in order)
| File | Change |
|------|--------|
| `python/helpers/plugins.py:25-34` | Extend `PluginMetadata` and `PluginListItem` with new fields |
| `python/helpers/plugins.py:61-93` | Update `get_enhanced_plugins_list` to populate new fields + `is_custom` |
| `plugins/memory/plugin.json` | Add `name`, `version`, `settings_sections: ["agent"]` |
| `plugins/example_agent/plugin.json` | Add `name`, `version`, `settings_sections: []` |
| `plugins/memory/webui/settings.html` | DELETE — recreate as `config.html` same content |
| `python/api/plugins.py` | Remove `list` action; fix function calls; rename actions |
| `webui/components/plugins/plugin-settings-store.js` | `settingsComponentHtml` getter: `settings.html` → `config.html`; action strings: `get_config`/`save_config` |
| `webui/components/settings/plugins/plugins-subsection.html` | Switch to `plugins_list` API, client-side filter by `settings_sections` |
| `webui/components/plugins/list/plugin-list.html` | Fix button styles; deduplicate tab card HTML |
| `webui/components/plugins/list/pluginListStore.js` | Add `selectedPlugin`, `openPlugin`, `openPluginConfig`, `openPluginInfo`, `deletePlugin` |
| `webui/components/plugins/plugin-info.html` | CREATE — new info modal |
| `plugins/README.md`, `skills/a0-create-plugin/SKILL.md`, `AGENTS.md` | Rename `settings_tabs`→`settings_sections`, `settings.html`→`config.html` |

### Reference Anchors
| File | Lines | Relevance |
|------|-------|-----------|
| `python/helpers/plugins.py` | 25-34 | `PluginMetadata` and `PluginListItem` — extend these |
| `python/helpers/plugins.py` | 61-93 | `get_enhanced_plugins_list` — update to pass new fields |
| `python/helpers/plugins.py` | 199-213 | `get_plugin_config` / `save_plugin_config` — call these from API |
| `webui/components/settings/skills/list.html` | 73-81 | Button style reference (`button`, `cancel icon-button`) |
| `webui/components/modals/scheduler/scheduler-task-detail.html` | 1-60 | Info modal layout reference (details grid) |
| `webui/components/plugins/list/pluginListStore.js` | 1-44 | Current store — extend with action methods |
| `webui/components/plugins/plugin-settings-store.js` | 100-120 | `settingsComponentHtml` getter to update |

---

## Ψ Knowledge Prerequisites

### Files to Read Before Starting
- [ ] `python/helpers/plugins.py:25-93` — understand current Pydantic models and `get_enhanced_plugins_list` structure
- [ ] `python/api/plugins.py:1-41` — see exactly what's broken (the three bad function calls)
- [ ] `webui/components/plugins/list/plugin-list.html:52-84` — button block to restyle + wire
- [ ] `webui/components/plugins/list/pluginListStore.js:1-44` — store to extend
- [ ] `webui/components/plugins/plugin-settings-store.js:100-120` — `settingsComponentHtml` getter
- [ ] `.cursor/plans/plugin_list_ui_+_schema_alignment_eb81a989.plan.md` — full plan

---

## Ω Forward Vector

### Next Actions (8 tasks in plan order)
1. **plugin-json-schema**: Extend `PluginMetadata`/`PluginListItem` in `plugins.py`; update both `plugin.json` files
2. **rename-config-html**: Delete `plugins/memory/webui/settings.html`; create `config.html`; update `plugin-settings-store.js` getter
3. **align-backend-api**: Fix `python/api/plugins.py` — remove `list` action, fix function calls, rename actions; update store action strings
4. **update-subsection**: Switch `plugins-subsection.html` to `plugins_list` API + client-side `settings_sections` filter
5. **fix-button-styles**: Restyle buttons in `plugin-list.html` + deduplicate tab HTML
6. **wire-store-actions**: Add `selectedPlugin` + 4 action methods to `pluginListStore.js`
7. **plugin-info-modal**: Create `webui/components/plugins/plugin-info.html`
8. **update-docs**: Update `README.md`, `SKILL.md`, `AGENTS.md`

### Success Criteria
- [ ] `PluginMetadata`/`PluginListItem` expose the 6 new fields; `get_enhanced_plugins_list` populates them
- [ ] `plugins/memory/webui/config.html` exists; `settings.html` deleted
- [ ] `python/api/plugins.py` uses only functions that exist in Jan's `plugins.py`
- [ ] Plugin list buttons styled like skills list; all three wired to real actions
- [ ] Plugin info modal opens showing correct data from `selectedPlugin`
- [ ] Docs updated

### Hazards / Watch Points
- `get_webui_extensions` returns `List[str]` — do not touch this function
- `plugin-settings-store.js` has `saveMode` branching — preserve it when editing the action strings
- Deduplicating `plugin-list.html` tab HTML must not break Bootstrap `.tab-pane.active` show/hide
- `plugins_list` API (Jan's) returns `{ ok, plugins: [...] }` — not `{ ok, data: [...] }`

---

## Glossary
| Term | Definition |
|------|------------|
| `settings_sections` | `plugin.json` field (renamed from `settings_tabs`) — list of settings tab IDs where plugin appears |
| `config.html` | Jan's convention for plugin config screen (was `settings.html` in our prior work) |
| `config.json` | Jan's convention for plugin config data file |
| `has_config_screen` | `PluginListItem` bool — `webui/config.html` exists |
| `has_main_screen` | `PluginListItem` bool — `webui/main.html` exists |
| `get_enhanced_plugins_list` | Jan's function returning `List[PluginListItem]` |
| `plugins_list` | Jan's API endpoint name (`python/api/plugins_list.py`), returns `{ ok, plugins }` |
| `saveMode` | `pluginSettings` store field: `'plugin'` or `'core'` — which API saves config |
