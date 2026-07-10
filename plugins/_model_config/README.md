# Model Configuration

Manage which models Agent Zero uses for chat, utility, and embeddings, with support for scoped overrides and reusable presets.

## What It Does

This plugin centralizes model selection and model-related settings for the application. It provides helpers and APIs for:

- selecting chat, utility, and embedding models
- reading and saving model presets
- checking for missing API keys
- allowing optional per-chat model overrides
- resolving config at global, project, agent, and chat scope

## Main Behavior

- **Scoped configuration**
  - Reads plugin config through the standard plugin config system with project and agent overrides.
- **Preset management**
  - Loads presets from a user file when present and falls back to bundled defaults.
  - Project presets can be stored beside a project's scoped model config.
- **Per-chat override**
  - Allows a chat context to store a temporary override or preset reference in context data.
- **Model object construction**
  - Builds `ModelConfig` objects and the runtime chat, utility, and embedding wrappers used elsewhere in the app.
- **API key validation**
  - Reports configured providers that still require API keys.

## Key Files

- **Core helper**
  - `helpers/model_config.py` resolves config, presets, overrides, and runtime model objects.
- **APIs**
  - `api/model_config_get.py`
  - `api/model_config_set.py`
  - `api/model_override.py`
  - `api/model_presets.py`
  - `api/model_search.py`
  - `api/api_keys.py`
- **Hooks**
  - `hooks.py` exposes plugin-level integration hooks.

## Configuration Scope

- **Settings section**: `agent`
- **Per-project config**: `true`
- **Per-agent config**: `true`
- **Always enabled**: `true`

## Project-Scoped Model Config

Projects store copied model settings in the standard scoped plugin path:

```text
/a0/usr/projects/<project>/.a0proj/plugins/_model_config/config.json
```

Project-only presets live beside that config:

```text
/a0/usr/projects/<project>/.a0proj/plugins/_model_config/presets.yaml
```

The project preset file uses the same plain YAML list schema as global presets. It does not contain scope metadata:

```yaml
- name: Research
  chat:
    provider: openrouter
    name: anthropic/claude-sonnet-5
    api_base: ""
    ctx_length: 200000
    ctx_history: 0.7
    vision: true
  utility:
    provider: openrouter
    name: openai/gpt-5.4-mini
```

Preset slots are partial overlays. Missing fields inherit from the current effective config, so a preset can switch only the model identity while preserving tuned context windows and rate limits. Provider-specific `kwargs` are replaced or cleared. The `utility` and `embedding` slots are optional and only apply when they declare a provider or model name; otherwise those configured models are inherited. Selecting a preset for a project writes the merged result into the project's `config.json`.

## Plugin Metadata

- **Name**: `_model_config`
- **Title**: `Model Configuration`
- **Description**: Manages LLM model selection and configuration for chat, utility, and embedding models. Supports per-project and per-agent overrides with optional per-chat model switching.
