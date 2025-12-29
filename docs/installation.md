# Users installation guide for Windows, macOS and Linux

Click to open a video to learn how to install Agent Zero:

[![Easy Installation guide](/docs/res/easy_ins_vid.png)](https://www.youtube.com/watch?v=w5v5Kjx51hs)

The following user guide provides instructions for installing and running Agent Zero using Docker, which is the primary runtime environment for the framework. For developers and contributors, we also provide instructions for setting up the [full development environment](#in-depth-guide-for-full-binaries-installation).


## Windows, macOS and Linux Setup Guide


1. **Install Docker Desktop:** 
- Docker Desktop provides the runtime environment for Agent Zero, ensuring consistent behavior and security across platforms
- The entire framework runs within a Docker container, providing isolation and easy deployment
- Available as a user-friendly GUI application for all major operating systems

1.1. Go to the download page of Docker Desktop [here](https://www.docker.com/products/docker-desktop/). If the link does not work, just search the web for "docker desktop download".

1.2. Download the version for your operating system. For Windows users, the Intel/AMD version is the main download button.

<img src="res/setup/image-8.png" alt="docker download" width="200"/>
<br><br>

> [!NOTE]
> **Linux Users:** You can install either Docker Desktop or docker-ce (Community Edition). 
> For Docker Desktop, follow the instructions for your specific Linux distribution [here](https://docs.docker.com/desktop/install/linux-install/). 
> For docker-ce, follow the instructions [here](https://docs.docker.com/engine/install/).
>
> If you're using docker-ce, you'll need to add your user to the `docker` group:
> ```bash
> sudo usermod -aG docker $USER
> ```
> Log out and back in, then run:
> ```bash
> docker login
> ```

1.3. Run the installer with default settings. On macOS, drag and drop the application to your Applications folder.

<img src="res/setup/image-9.png" alt="docker install" width="300"/>
<img src="res/setup/image-10.png" alt="docker install" width="300"/>

<img src="res/setup/image-12.png" alt="docker install" width="300"/>
<br><br>

1.4. Once installed, launch Docker Desktop: 

<img src="res/setup/image-11.png" alt="docker installed" height="100"/>
<img src="res/setup/image-13.png" alt="docker installed" height="100"/>
<br><br>

> [!NOTE]
> **MacOS Configuration:** In Docker Desktop's preferences (Docker menu) → Settings → 
> Advanced, enable "Allow the default Docker socket to be used (requires password)."

![docker socket macOS](res/setup/macsocket.png)

2. **Run Agent Zero:**

- Note: The Hacker profile is included in the main image. After launch, choose the **hacker** agent profile in Settings if you want the security-focused prompts and tooling.

2.1. Pull the Agent Zero Docker image:
- Search for `agent0ai/agent-zero` in Docker Desktop
- Click the `Pull` button
- The image will be downloaded to your machine in a few minutes

![docker pull](res/setup/1-docker-image-search.png)

> [!TIP]
> Alternatively, run the following command in your terminal:
>
> ```bash
> docker pull agent0ai/agent-zero
> ```

2.2. OPTIONAL - Map specific folders for persistence:

> [!CAUTION]
> The recommended persistence and upgrade workflow is to use **Settings → Backup & Restore**.
> Do **not** map the entire `/a0` directory: it contains the application code and can break upgrades.

- Only map the folders you need to keep outside the container, such as:
  - `/a0/work_dir` for files you want the agent to manipulate directly
  - `/a0/usr/projects` for project workspaces
  - `/a0/memory` or `/a0/knowledge` if you explicitly want to persist those between restarts

> [!TIP]
> If you need long-term persistence across upgrades, use Backup & Restore and keep a copy of `/a0/tmp/secrets.env` (secrets are not always included in backups).

2.3. Run the container:
- In Docker Desktop, go back to the "Images" tab
- Click the `Run` button next to the `agent0ai/agent-zero` image
- Open the "Optional settings" menu
- **Ensure at least one host port is mapped to container port `80`** (set host port to `0` for automatic assignment)

Optionally you can map local folders for file persistence:
> [!CAUTION]
> Preferred way of persisting Agent Zero data is to use the backup and restore feature.
> By mapping the whole `/a0` directory to a local directory, you will run into problems when upgrading Agent Zero to a newer version.
- OPTIONAL: Under "Volumes", configure your mapped folders, if needed:
  - Example host path: Your chosen directory (e.g., `C:\agent-zero\memory`)
  - Example container path: `/a0/memory`


- Click the `Run` button in the "Images" tab.

![docker port mapping](res/setup/2-docker-image-run.png)
![docker port mapping](res/setup/2-docker-image-run2.png)

- The container will start and show in the "Containers" tab

![docker containers](res/setup/4-docker-container-started.png)

> [!TIP]
> Alternatively, run the following command in your terminal:
> ```bash
> docker run -p 0:80 -v /path/to/your/work_dir:/a0/work_dir agent0ai/agent-zero
> ```
> - Replace `0` with a fixed port if you prefer (e.g., `50080:80`)
> - Map only the folders you need (e.g., `/a0/work_dir`, `/a0/usr/projects`), not the entire `/a0` directory

2.4. Access the Web UI:
- The framework will take a few seconds to initialize and the Docker logs will look like the image below.
- Find the mapped port in Docker Desktop (shown as `<PORT>:80`) or click the port right under the container ID as shown in the image below

![docker logs](res/setup/5-docker-click-to-open.png)

- Open `http://localhost:<PORT>` in your browser
- The Web UI will open. Agent Zero is ready for configuration!

![docker ui](res/setup/6-docker-a0-running.png)

> [!TIP]
> You can also access the Web UI by clicking the ports right under the container ID in Docker Desktop.

> [!NOTE]
> If you mapped specific folders (such as `/a0/work_dir`), those files are accessible on your host and changes are reflected in the container. If you did not map folders, use the built-in File Browser and Backup & Restore to manage data.

3. Configure Agent Zero
- Refer to the following sections for a full guide on how to configure Agent Zero.

## Settings Configuration
Agent Zero provides a comprehensive settings interface to customize various aspects of its functionality. Access the settings by clicking the "Settings"button with a gear icon in the sidebar.

### Agent Configuration
- **Agent Profile:** Select the agent profile (e.g., `agent0`, `hacker`, `researcher`). Profiles can override prompts, tools, and extensions.
- **Memory Subdirectory:** Select the subdirectory for agent memory storage, allowing separation between different instances.
- **Knowledge Subdirectory:** Specify the location of custom knowledge files to enhance the agent's understanding.

> [!NOTE]
> Since v0.9.7, custom prompts belong in `/a0/agents/<agent_name>/prompts/` rather than a shared `/prompts` folder. See the [Extensibility guide](extensibility.md#prompts) for details.

![settings](res/setup/settings/1-agentConfig.png)

### Chat Model Settings
- **Provider:** Select the chat model provider (e.g., Ollama)
- **Model Name:** Choose the specific model (e.g., llama3.2)
- **API URL:** URL of the API endpoint for the chat model - only needed for custom providers like Ollama, Azure, etc.
- **Context Length:** Set the maximum token limit for context window
- **Context Window Space:** Configure how much of the context window is dedicated to chat history

![chat model settings](res/setup/settings/2-chat-model.png)

> [!IMPORTANT]
> **Model naming is provider-specific.** Use `gpt-4.1` for OpenAI, but use `openai/gpt-4.1` for OpenRouter. If you see “Invalid model ID,” verify the provider and naming format.

> [!TIP]
> **Context window tuning:** Set the total context window size first (for example, 100k), then adjust the chat history portion as a fraction of that total. A large fraction on a very large context window can still be enormous.

### Utility Model Configuration
- **Provider & Model:** Select a model for utility tasks like memory organization and summarization
- **Temperature:** Adjust the determinism of utility responses

> [!NOTE]
> Utility models need to be strong enough to extract and consolidate memory reliably. Very small models (e.g., 4B) often fail at this; 70B-class models or high-quality cloud “flash/mini” models work best.

### Embedding Model Settings
- **Provider:** Choose the embedding model provider (e.g., OpenAI)
- **Model Name:** Select the specific embedding model (e.g., text-embedding-3-small)

> [!NOTE]
> Agent Zero uses a local embedding model by default (tiny footprint), but you can switch to OpenAI embeddings like `text-embedding-3-small` or `text-embedding-3-large` if preferred.

### Speech to Text Options
- **Model Size:** Choose the speech recognition model size
- **Language Code:** Set the primary language for voice recognition
- **Silence Settings:** Configure silence threshold, duration, and timeout parameters for voice input

### API Keys
- Configure API keys for various service providers directly within the Web UI
- Click `Save` to confirm your settings

> [!NOTE]
> **OpenAI API vs Plus subscription:** A ChatGPT Plus subscription does not include API credits. You must provide a separate API key for OpenAI usage in Agent Zero.

> [!TIP]
> For OpenAI-compatible providers (e.g., custom gateways or Z.AI/GLM), add the API key under **External Services → Other OpenAI-compatible API keys**, then select **OpenAI Compatible** as the provider in model settings.

> [!CAUTION]
> **GitHub Copilot Provider:** When using the GitHub Copilot provider, after selecting the model and entering your first prompt, the OAuth login procedure will begin. You'll find the authentication code and link in the output logs. Complete the authentication process by following the provided link and entering the code, then you may continue using Agent Zero.

> [!NOTE]
> **GitHub Copilot Limitations:** GitHub Copilot models typically have smaller rate limits and context windows compared to models hosted by other providers like OpenAI, Anthropic, or Azure. Consider this when working with large conversations or high-frequency requests.



### Authentication
- **UI Login:** Set username for web interface access
- **UI Password:** Configure password for web interface security
- **Root Password:** Manage Docker container root password for SSH access

![settings](res/setup/settings/3-auth.png)

### Development Settings
- **RFC Parameters (local instances only):** configure URLs and ports for remote function calls between instances
- **RFC Password:** Configure password for remote function calls
Learn more about Remote Function Calls in the [Development guide](development.md#step-6-configure-ssh-and-rfc-connection).

> [!IMPORTANT]
> Always keep your API keys and passwords secure.

> [!NOTE]
> On Windows host installs (non-Docker), you must use RFC to run shell code on the host system. The Docker runtime handles this automatically.

# Choosing Your LLMs
The Settings page is the control center for selecting the Large Language Models (LLMs) that power Agent Zero.  You can choose different LLMs for different roles:

| LLM Role | Description |
| --- | --- |
| `chat_llm` | This is the primary LLM used for conversations and generating responses. |
| `utility_llm` | This LLM handles internal tasks like summarizing messages, managing memory, and processing internal prompts.  Using a smaller, less expensive model here can improve efficiency. |
| `embedding_llm` | This LLM is responsible for generating embeddings used for memory retrieval and knowledge base lookups. Changing the `embedding_llm` will re-index all of A0's memory. |

**How to Change:**
1. Open Settings page in the Web UI.
2. Choose the provider for the LLM for each role (Chat model, Utility model, Embedding model) and write the model name.
3. Click "Save" to apply the changes.

## Important Considerations
### Model Naming by Provider
Use the naming format required by your selected provider:

| Provider | Model Name Format | Example |
| --- | --- | --- |
| OpenAI | Model name only | `gpt-4.1` |
| OpenRouter | Provider prefix required | `openai/gpt-4.1` |
| Venice AI | Model name with optional parameters | `qwen3-235b:disable_thinking=true` |
| Ollama | Model name only | `llama3.2` |

> [!IMPORTANT]
> Remove `openai/` when using the native OpenAI provider. That prefix is only for OpenRouter.

> [!TIP]
> Venice model parameters can be appended directly to the model name, for example:
> `qwen3-235b:disable_thinking=true&include_venice_system_prompt=false`

### Context Window & Memory Split
- Set the **total context window** (e.g., 100k) first.
- Then tune the **chat history portion** as a fraction of that total.
- Extremely large totals can make even small fractions very large; adjust thoughtfully.

### Utility Model Guidance
- Utility models handle summarization and memory extraction.
- Very small models (≈4B) usually fail at reliable memory extraction.
- Aim for ~70B class models or strong cloud “flash/mini” models for better results.

### Reasoning/Thinking Models
- Reasoning can increase cost and latency. Some models perform better **without** reasoning.
- If a model supports it, disable reasoning via provider-specific parameters (e.g., Venice `disable_thinking=true`).

## Installing and Using Ollama (Local Models)
If you're interested in Ollama, which is a powerful tool that allows you to run various large language models locally, here's how to install and use it:

#### First step: installation
**On Windows:**

Download Ollama from the official website and install it on your machine.

<button>[Download Ollama Setup](https://ollama.com/download/OllamaSetup.exe)</button>

**On macOS:**
```
brew install ollama
```
Otherwise choose macOS installer from the [official website](https://ollama.com/).

**On Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Finding Model Names:**
Visit the [Ollama model library](https://ollama.com/library) for a list of available models and their corresponding names. Ollama models are referenced by **model name only** (for example, `llama3.2`).

#### Second step: pulling the model
**On Windows, macOS, and Linux:**
```
ollama pull <model-name>
```

1. Replace `<model-name>` with the name of the model you want to use.  For example, to pull the Mistral Large model, you would use the command `ollama pull mistral-large`.

2. A CLI message should confirm the model download on your system

#### Selecting your model within Agent Zero
1. Once you've downloaded your model(s), you must select it in the Settings page of the GUI. 

2. Within the Chat model, Utility model, or Embedding model section, choose Ollama as provider.

3. Write your model code as expected by Ollama, in the format `llama3.2` or `qwen2.5:7b`

4. Provide your API base URL to your ollama API endpoint, usually `http://host.docker.internal:11434`

5. Click `Save` to confirm your settings.

![ollama](res/setup/settings/4-local-models.png)

> [!NOTE]
> If Agent Zero runs in Docker and Ollama runs on the host, ensure port **11434** is reachable from the container. If both services are in the same Docker network, you can use `http://<container_name>:11434` instead of `host.docker.internal`.

#### Managing your downloaded models
Once you've downloaded some models, you might want to check which ones you have available or remove any you no longer need.

- **Listing downloaded models:** 
  To see a list of all the models you've downloaded, use the command:
  ```
  ollama list
  ```
- **Removing a model:**
  If you need to remove a downloaded model, you can use the `ollama rm` command followed by the model name:
  ```
  ollama rm <model-name>
  ```


- Experiment with different model combinations to find the balance of performance and cost that best suits your needs. E.g., faster and lower latency LLMs will help, and you can also use `faiss_gpu` instead of `faiss_cpu` for the memory.

## Using Agent Zero on your mobile device
Agent Zero's Web UI is accessible from any device on your network through the Docker container:

> [!NOTE]
> In settings, External Services tab, you can enable Cloudflare Tunnel to expose your Agent Zero instance to the internet.
> ⚠️ Do not forget to set username and password in the settings Authentication tab to secure your instance on the internet.

1. The Docker container automatically exposes the Web UI on all network interfaces
2. Find the mapped port in Docker Desktop:
   - Look under the container name (usually in the format `<PORT>:80`)
   - For example, if you see `32771:80`, your port is `32771`
3. Access the Web UI from any device using:
   - Local access: `http://localhost:<PORT>`
   - Network access: `http://<YOUR_COMPUTER_IP>:<PORT>`

> [!TIP]
> - Your computer's IP address is usually in the format `192.168.x.x` or `10.0.x.x`
> - You can find your external IP address by running `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
> - The port is automatically assigned by Docker unless you specify one

> [!NOTE]
> If you're running Agent Zero directly on your system (legacy approach) instead of 
> using Docker, you'll need to configure the host manually in `run_ui.py` to run on all interfaces using `host="0.0.0.0"`.

For developers or users who need to run Agent Zero directly on their system,see the [In-Depth Guide for Full Binaries Installation](#in-depth-guide-for-full-binaries-installation).

# How to update Agent Zero

> [!NOTE]
> Since v0.9, Agent Zero includes a Backup & Restore workflow in the Settings UI. This is the **safest** way to upgrade Docker instances.

## Recommended Update Process (Docker)
1. **Keep the old container running** and note its port.
2. **Pull the new image** (`agent0ai/agent-zero:latest`).
3. **Start a new container** on a different host port.
4. In the **old** instance, open **Settings → Backup & Restore** and create a backup.
5. In the **new** instance, restore that backup from the same panel.
6. **Manually copy secrets** from `/a0/tmp/secrets.env` if you rely on them (secrets are not always included in backups).

> [!TIP]
> If the new instance fails to load settings, remove `/a0/tmp/settings.json` and restart to regenerate defaults.

## Manual Migration (Legacy or Non-Docker)
If you are migrating from older, non-Docker setups, copy these directories into your new instance:
- `/memory` (agent memories)
- `/knowledge` (custom knowledge)
- `/instruments` (custom instruments)
- `/tmp/settings.json` (settings)
- `/tmp/chats/` (chat history)
- `/tmp/secrets.env` (secrets)

Then proceed with the Docker installation steps above.

      
### Conclusion
After following the instructions for your specific operating system, you should have Agent Zero successfully installed and running. You can now start exploring the framework's capabilities and experimenting with creating your own intelligent agents. 

If you encounter any issues during the installation process, please consult the [Troubleshooting section](troubleshooting.md) of this documentation or refer to the Agent Zero [Skool](https://www.skool.com/agent-zero) or [Discord](https://discord.gg/B8KZKNsPpj) community for assistance.
