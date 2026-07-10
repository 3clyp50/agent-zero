# Gemini CLI

Use Gemini CLI for headless Google Gemini coding tasks. Always pass `-p`; bare `gemini` opens the interactive TUI.

## Install And Probe

```bash
command -v gemini >/dev/null || npm install -g @google/gemini-cli
gemini --version
gemini --help
```

## Smoke Prompt

```bash
cd "$WORKDIR"
gemini -p "Respond exactly: TERMINAL_AGENT_SMOKE_OK" --output-format json --approval-mode=yolo --skip-trust
```

## Login

Headless mode uses existing cached Google credentials, a Gemini API key, or Vertex AI credentials. Do not start bare `gemini` through Agent Zero for login; it opens a TUI. For local browser sign-in, ask the user to run `gemini` in their own terminal, select **Sign in with Google**, finish in the browser, and then retry the smoke prompt.

For container automation, prefer `GEMINI_API_KEY`. Ask the user to add it through **Settings > External Services > Secrets Management**, then source `/a0/usr/.env` without printing it:

```bash
set -a
. /a0/usr/.env
set +a
```

Vertex AI may instead use `GOOGLE_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`, or cached Application Default Credentials. It also requires `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`. Never ask the user to paste keys or service-account JSON into chat.

## Real Task

```bash
cd "$WORKDIR"
gemini -p "$TASK" --output-format json --approval-mode=yolo --skip-trust
```

Add `-m "$MODEL"` only when the user or settings provide a model override. Use `--approval-mode=plan` instead of `yolo` when the user explicitly asks for read-only analysis.
