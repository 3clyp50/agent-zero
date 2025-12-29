# Quick Start
This guide provides a quick introduction to using Agent Zero. We'll cover launching the Web UI, starting a new chat, and running a simple task.

## Launching the Web UI (Docker)
1. Make sure you have Agent Zero installed (see the [Installation guide](installation.md)).
2. Run the container and map a host port to container port **80**.
   - In Docker Desktop, choose **Optional settings** and set the host port (use `0` for a random port).
   - On the CLI, run:

```bash
docker run -p 50080:80 agent0ai/agent-zero:latest
```

3. Open your browser and navigate to the mapped port (for example `http://localhost:50080`).
4. You should see the Agent Zero Web UI:

![New Chat](res/ui_newchat1.png)

> [!TIP]
> The Web UI has quick chat management buttons (New, Reset, Save, Load). Chats are stored under `/a0/tmp/chats/` inside the container.

## Running a Simple Task
Let's ask Agent Zero to download a YouTube video. Here's how:

1. Type "Download a YouTube video for me" in the chat input field and press Enter or click the send button.
2. Agent Zero will process your request and outline the steps it plans to take.
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
> The [Usage Guide](usage.md) provides more in-depth information on using Agent Zero's features, including tools, projects, tasks, and backup/restore.
