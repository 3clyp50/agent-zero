# Quick Start
This guide provides a quick introduction to using Agent Zero. We'll cover launching the Web UI, starting a new chat, and running a simple task.

## Launching the Web UI (Docker)
1. Pull the latest image:

```bash
docker pull agent0ai/agent-zero:latest
```

2. Run the container and let Docker assign a port:

```bash
docker run -p 0:80 agent0ai/agent-zero:latest
```

3. Find the mapped port:
   - Docker Desktop: look under the container for `<PORT>:80`
   - CLI: run `docker ps` and check the Ports column

4. Open the Web UI in your browser:

```
http://localhost:<PORT>
```

5. Open **Settings** and configure your API keys and models.

> [!TIP]
> If you are developing locally (not Docker), use `python run_ui.py` and follow the [development guide](development.md).

> [!NOTE]
> Chat history is stored in `/a0/tmp/chats/` inside the container.

![New Chat](res/ui_newchat1.png)

> [!TIP]
> The Web UI provides quick chat management buttons: `New Chat`, `Reset Chat`, `Save Chat`, and `Load Chat`.

## Running a Simple Task
Let's ask Agent Zero to download a YouTube video. Here's how:

1. Type "Download a YouTube video for me" in the chat input field and press Enter or click the send button.
2. Agent Zero will process your request. You'll see its thoughts and tool calls in the UI.
3. The agent will ask you for the URL of the YouTube video you want to download.

## Example Interaction
Here's an example of what you might see in the Web UI at step 3:

![1](res/image-24.png)

## Next Steps
Now that you've run a simple task, you can experiment with more complex requests. Try asking Agent Zero to:

* Perform calculations
* Search the web for information
* Execute shell commands
* Explore web development tasks
* Create or modify files

> [!TIP]
> The [Usage Guide](usage.md) provides more in-depth information on tools, projects, tasks, and backup/restore.
