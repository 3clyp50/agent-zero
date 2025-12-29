# Troubleshooting and FAQ
This page addresses frequently asked questions (FAQ) and provides troubleshooting steps for common issues encountered while using Agent Zero.

## Frequently Asked Questions

**1. How do I ask Agent Zero to work directly on my files or directories?**
- Place the files/dirs in `/a0/work_dir` (or map that folder from your host). Agent Zero will operate inside this working directory by default.

**2. When I input something in the chat, nothing happens. What's wrong?**
- Check that API keys are configured in **Settings → External Services**. Without valid keys, Agent Zero cannot call LLM providers.

**3. How do I integrate open-source models with Agent Zero?**
- Refer to [Installing and Using Ollama](installation.md#installing-and-using-ollama-local-models) for local model setup. LM Studio can also be used via OpenAI-compatible APIs.

**4. Where is chat history stored?**
- Chat history JSON files live in `/a0/tmp/chats/` inside the container.

**5. How do I retain memory and settings between updates?**
- Use **Settings → Backup & Restore** to export and restore data between versions.

**6. I lost secrets after a backup/restore.**
- Secrets are stored in `/a0/tmp/secrets.env` and are **not** included in backups. Copy this file manually.

**7. Why does OpenAI say I have no credits even though I have Plus?**
- OpenAI Plus subscriptions do **not** include API credits. You need a separate API key.

## Troubleshooting

### Installation & Docker
- **Web UI not reachable:** Ensure at least one host port is mapped to container port `80` (e.g., `0:80` for random).
- **Ollama connection issues:** Expose port `11434` and use `http://host.docker.internal:11434` or `http://containerName:11434` if on the same Docker network.

### Models & Providers
- **Invalid model ID:** Make sure the model name format matches the provider. Remove `openai/` prefix for OpenAI; use it for OpenRouter.
- **Context window errors:** Set total context length first (e.g., `100k`), then set the history ratio. Very high total sizes can cause confusion.
- **Temperature parameter errors:** If a provider rejects `temperature=0`, remove the custom parameter from all model configs.

### Browser Agent
- **Browser agent failing or unstable:** This is a known issue. Prefer MCP alternatives such as Browser OS, Chrome DevTools MCP, or Playwright MCP. See [MCP Setup](mcp_setup.md).

### UI & Responses
- **Large responses appear truncated:** The UI stores responses longer than ~500 characters in files to prevent freezing. Ask the agent to open the file or check the file browser.

### Performance
- **Agent is slow with local models:** Remember that Docker adds overhead. Consider reducing context length or using a stronger model for utility/memory tasks.

> [!TIP]
> If the agent gets stuck after changing settings, start a **new chat**. It’s often easier to reset than to convince an agent to change course mid-session.
