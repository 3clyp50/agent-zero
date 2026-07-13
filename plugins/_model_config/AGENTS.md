# Model Configuration Plugin DOX

## Purpose

- Own LLM model selection, presets, API-key checks, scoped overrides, and model settings UI.

## Ownership

- `helpers/model_config.py` owns config resolution, presets, overrides, and runtime model object construction.
- `api/` owns model config, override, preset, search, and API-key endpoints.
- `webui/` owns model settings, summaries, switcher, and API-key UI.
- `default_config.yaml`, `default_presets.yaml`, `provider_metadata.yaml`, `hooks.py`, and `plugin.yaml` own defaults, metadata, hooks, and manifest.

## Local Contracts

- Preserve global, project, agent, and chat override resolution order.
- Project Settings `llm` payloads are owned here through the generic `helpers.projects` project extension-data hooks; keep project helper code agnostic to `_model_config` paths, presets, and inheritance rules.
- Keep provider metadata and API-key checks safe around secrets.
- Coordinate OAuth-backed providers with `_oauth` instead of hardcoding provider-specific auth here.
- `model_config_get` exposes `model_configured` as a derived chat-model readiness flag from provider, model name, and API-key availability.
- Applying a model preset may inherit durable tuning such as context windows and rate limits, but must replace or clear per-slot `kwargs` so provider-specific extra params never leak across model providers.
- Changing a model provider in the settings UI must clear `api_base` and `kwargs` because both may be provider-specific.
- Repair provider-specific model-config aliases at the model-config read/build boundary; keep provider-specific repairs out of provider-agnostic core wrappers such as `models.py`.
- `modelConfig.createPresetEditor()` owns local preset drafts, row actions, and stable UI-only row keys so deletion or renaming cannot rebind nested model fields.
- Preset editor reset actions must remove the user override through the preset API and refresh the open draft from bundled defaults.
- Model-name catalogs open below the input from either a field click or the embedded magnifier.

## Work Guidance

- Keep backend model config shape and frontend settings fields synchronized.

## Verification

- Run model-config and onboarding-related tests when model provider, preset, or API-key behavior changes.

## Child DOX Index

No child DOX files.
