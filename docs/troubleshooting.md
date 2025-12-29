# Troubleshooting and FAQ
This page addresses frequently asked questions (FAQ) and provides troubleshooting steps for common issues encountered while using Agent Zero.

## Frequently Asked Questions
**1. How do I ask Agent Zero to work directly on my files or dirs?**
-   Place the files/dirs in the `work_dir` directory. Agent Zero will be able to perform tasks on them. The `work_dir` directory is located in the root directory of the Docker Container.

**2. When I input something in the chat, nothing happens. What's wrong?**
-   Check if you have set up API keys in the Settings page. If not, the application will not be able to communicate with the endpoints it needs to run LLMs and to perform tasks.

**3. I get “invalid model ID.” What does that mean?**
-   You likely selected the wrong provider for the model name. For example, `openai/gpt-4.1` only works with **OpenRouter**. For native OpenAI, use `gpt-4.1`.

**4. Does OpenAI Plus include API credits?**
-   No. You need a paid OpenAI API key from the API dashboard.

**5. How do I integrate open-source models with Agent Zero?**
Refer to the [Ollama setup](installation.md#installing-and-using-ollama-local-models) section for local models. Ensure port **11434** is reachable from the container.

> [!TIP]
> Some LLM providers offer free usage of their APIs, for example Groq, Mistral, SambaNova or CometAPI.

**6. Why can’t I access the Web UI?**
-   Ensure you mapped at least one host port to container port **80** (or used host port `0` for an auto-assigned port).

**7. How can I make Agent Zero retain memory between sessions?**
-   Use **Backup & Restore** in Settings. Avoid mapping the entire `/a0` directory.

**8. Where is chat history stored?**
-   Chat history lives in `/a0/tmp/chats/`.

**9. My secrets disappeared after restore.**
-   Secrets are stored in `/a0/tmp/secrets.env`. Copy this file manually after restoring.

**10. The browser agent fails or is unstable.**
-   The built-in browser agent can have dependency issues. Use MCP browser servers (BrowserOS, Chrome DevTools, Playwright) instead.

**11. How do I adjust API rate limits?**
Modify the `rate_limit_seconds` and `rate_limit_requests` parameters in the `AgentConfig` class within `initialize.py`.

**12. Can Agent Zero interact with external APIs or services (e.g., WhatsApp)?**
Extending Agent Zero to interact with external APIs is possible by creating custom tools or solutions. Refer to the documentation on creating them. 

## Troubleshooting

**Installation**
- **Docker Issues:** If Docker containers fail to start, consult the Docker documentation and verify your Docker installation and configuration. On macOS, ensure you've granted Docker access to your project files in Docker Desktop's settings as described in the [Installation guide](installation.md#windows-macos-and-linux-setup-guide). Verify that the Docker image is updated.
- **Ollama Connectivity:** If local models are unreachable, confirm port **11434** is accessible from the container (`http://host.docker.internal:11434` or `http://<container_name>:11434` on a shared Docker network).

**Usage**

- **Terminal commands not executing:** Ensure the Docker container is running and properly configured.  Check SSH settings if applicable. Check if the Docker image is updated by removing it from Docker Desktop app, and subsequently pulling it again.
- **Context window errors:** Reduce the total context window size or lower the chat history allocation to avoid oversized prompts.
- **Temperature parameter errors:** If you set `temperature=0` as an extra parameter and see errors, remove it from model settings and retry.

* **Error Messages:** Pay close attention to the error messages displayed in the Web UI or terminal.  They often provide valuable clues for diagnosing the issue. Refer to the specific error message in online searches or community forums for potential solutions.

* **Performance Issues:** If Agent Zero is slow or unresponsive, it might be due to resource limitations, network latency, or the complexity of your prompts and tasks, especially when using local models.
