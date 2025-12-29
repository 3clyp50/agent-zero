# Troubleshooting and FAQ
This page addresses frequently asked questions (FAQ) and provides troubleshooting steps for common issues encountered while using Agent Zero.

## Frequently Asked Questions

**1. How do I ask Agent Zero to work directly on my files or directories?**
- Place the files in `/a0/work_dir` (or a mapped folder you mounted into the container). The agent’s working directory defaults to `/work_dir` inside the container.

**2. When I input something in the chat, nothing happens. What’s wrong?**
- Ensure you configured API keys in **Settings → External Services**. Without a working LLM provider, the agent cannot respond.

**3. How do I integrate open-source models (Ollama, LM Studio, etc.)?**
- See [Installing and Using Ollama](installation.md#installing-and-using-ollama-local-models). Ensure port **11434** is reachable from the container.

**4. How do I retain memory and settings between updates?**
- Use **Settings → Backup & Restore**. Avoid mapping the entire `/a0` directory, which causes upgrade issues.

**5. Where are chat logs stored?**
- Chat history lives under `/a0/tmp/chats/`.

**6. My OpenAI Plus subscription isn’t working.**
- Plus does **not** include API credits. You still need an API key for Agent Zero.

**7. My browser agent keeps failing.**
- The built-in browser agent is currently unstable. Use MCP-based alternatives (Browser OS, Chrome DevTools, Playwright) instead. See [MCP setup](mcp_setup.md).

**8. Secrets disappeared after backup/restore.**
- Secrets are stored in `/a0/tmp/secrets.env` and are **not** included in backups. Copy this file manually.

---

## Common Errors & Fixes

### Invalid Model ID
**Symptom:** "Invalid model ID" or provider errors.  
**Fix:** Ensure the model name matches the provider:
- **OpenAI:** use `gpt-4.1` (no `openai/` prefix)
- **OpenRouter:** use `openai/gpt-4.1`

### Context Window Issues
**Symptom:** Truncated or missing context.  
**Fix:** Set total context window size (e.g., `100k`) and then allocate memory portion. Avoid overly large totals with large memory percentages.

### Utility Model Too Small
**Symptom:** Poor memory extraction or unreliable summaries.  
**Fix:** Use a stronger utility model (community guidance: ~70B+ or a strong hosted fast model).

### Temperature Parameter Errors
**Symptom:** Provider rejects requests or returns errors about temperature.  
**Fix:** Remove `temperature=0` or unsupported parameters from model settings and retry.

### 403 / WAF Errors (Venice API)
**Symptom:** 403 or WAF-blocked responses.  
**Fix:** This is typically a WAF restriction. Check provider status and retry; consider disabling automated retries if the endpoint blocks bots.

---

## Docker & Runtime Issues

- **Container won’t start:** Restart Docker Desktop and ensure the image is up to date.
- **Web UI not accessible:** Confirm that a host port is mapped to container port **80**.
- **Terminal commands not executing:** Verify the container is running and that you are using the correct shell tool.

---

## More Help
- Join the Agent Zero [Skool](https://www.skool.com/agent-zero) or [Discord](https://discord.gg/B8KZKNsPpj) community.
- Review [Installation](installation.md) and [Usage](usage.md) guides for advanced configuration.
