# Agent Zero: MCP Client Integration Guide

This guide explains how to configure and utilize external tool providers through the Model Context Protocol (MCP) with Agent Zero. This allows Agent Zero to leverage tools hosted by separate local or remote MCP-compliant servers.

> [!NOTE]
> This guide covers Agent Zero as an MCP **client**. To expose Agent Zero as an MCP **server**, see [Connectivity → MCP Server](connectivity.md#mcp-server-connectivity).

## What are MCP Servers?

MCP servers are external processes or services that expose a set of tools that Agent Zero can use. Agent Zero acts as an MCP *client*, consuming tools made available by these servers. The integration supports three main types of MCP servers:

1.  **Local Stdio Servers**: These are typically local executables that Agent Zero communicates with via standard input/output (stdio).
2.  **Remote SSE Servers**: These are servers, often accessible over a network, that Agent Zero communicates with using Server-Sent Events (SSE), usually over HTTP/S.
3.  **Remote Streaming HTTP Servers**: These are servers that use the streamable HTTP transport protocol for MCP communication, providing an alternative to SSE for network-based MCP servers.

## How Agent Zero Consumes MCP Tools

Agent Zero discovers and integrates MCP tools dynamically:

1.  **Configuration**: You define the MCP servers Agent Zero should connect to in its configuration. The primary way to do this is through the Agent Zero settings UI.
2.  **Saving Settings**: When you save your settings via the UI, Agent Zero updates the `tmp/settings.json` file, specifically the `"mcp_servers"` key.
3.  **Server Startup**: Agent Zero initializes configured MCP servers (stdio servers) or connects to them (remote servers). For `npx`/`uvx` based servers, the first run may download packages.
4.  **Tool Discovery**: Upon initialization (or when settings are updated), Agent Zero connects to each configured and enabled MCP server and queries it for the list of available tools, their descriptions, and expected parameters.
5.  **Dynamic Prompting**: The information about these discovered tools is then dynamically injected into the agent's system prompt. A placeholder like `{{tools}}` in a system prompt template (e.g., `prompts/agent.system.mcp_tools.md`) is replaced with a formatted list of all available MCP tools. This allows the agent's underlying Language Model (LLM) to know which external tools it can request.
6.  **Tool Invocation**: When the LLM decides to use an MCP tool, Agent Zero's `process_tools` method (handled by `mcp_handler.py`) identifies it as an MCP tool and routes the request to the appropriate `MCPConfig` helper, which then communicates with the designated MCP server to execute the tool.

## Recommended MCP Servers
Community-tested MCP servers include:

- **Browser OS MCP** (browser automation)
- **Chrome DevTools MCP** (browser automation)
- **Playwright MCP** (browser automation)
- **n8n MCP** (workflow automation)
- **Gmail MCP** (email workflows)

> [!TIP]
> The built-in browser agent can be unreliable; MCP-based browser tools are the recommended alternative.

## Docker Networking Notes
If Agent Zero runs in Docker and your MCP server runs on the host:

- Use `host.docker.internal` when available (macOS/Windows).
- On Linux, run the MCP server in the same Docker network and reference it by container name.

If your MCP server is remote, use its HTTPS URL in the configuration.

## Configuration

### Configuration File & Method

The primary method for configuring MCP servers is through **Agent Zero's settings UI**.

When you input and save your MCP server details in the UI, these settings are written to:

*   `tmp/settings.json`

### The `mcp_servers` Setting in `tmp/settings.json`

Within `tmp/settings.json`, the MCP servers are defined under the `"mcp_servers"` key.

*   **Value Type**: The value for `"mcp_servers"` must be a **JSON formatted string**. The string itself contains either:
    *   A JSON object containing `"mcpServers"` (recommended, matches the Settings UI)
    *   A JSON array of server configuration objects
*   **Default Value**: An empty config (for example, `{"mcpServers": {}}`).
*   **Manual Editing (Advanced)**: While UI configuration is recommended, you can also manually edit `tmp/settings.json`. If you do, ensure the `"mcp_servers"` value is a valid JSON string, with internal quotes properly escaped.

**Example `mcp_servers` configuration (recommended format):**

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "/root/db.sqlite"]
    },
    "deep-wiki": {
      "description": "Use this MCP to analyze GitHub repositories",
      "url": "https://mcp.deepwiki.com/sse"
    }
  }
}
```
*Note: In `tmp/settings.json`, the entire value of `"mcp_servers"` is stored as a single string. The Settings UI handles escaping automatically.*

*   **Updating**: As mentioned, the recommended way to set or update this value is through Agent Zero's settings UI.
*   **For Existing `settings.json` Files (After an Upgrade)**: If you have an existing `tmp/settings.json` from a version of Agent Zero prior to MCP server support, the `"mcp_servers"` key will likely be missing. To add this key:
    1.  Ensure you are running a version of Agent Zero that includes MCP server support.
    2.  Run Agent Zero and open its settings UI.
    3.  Save the settings (even without making changes). This action will write the complete current settings structure, including a default `"mcp_servers": ""` if not otherwise populated, to `tmp/settings.json`. You can then configure your servers via the UI or by carefully editing this string.

### MCP Server Configuration Structure

Here are templates for configuring individual servers within the `mcp_servers` configuration:

**1. Local Stdio Server**

```json
{
    "name": "My Local Tool Server",
    "description": "Optional: A brief description of this server.",
    "type": "stdio", // Optional: Explicitly specify server type. Can be "stdio", "sse", or streaming HTTP variants ("http-stream", "streaming-http", "streamable-http", "http-streaming"). Auto-detected if omitted.
    "command": "python", // The executable to run (e.g., python, /path/to/my_tool_server)
    "args": ["path/to/your/mcp_stdio_script.py", "--some-arg"], // List of arguments for the command
    "env": { // Optional: Environment variables for the command's process
        "PYTHONPATH": "/path/to/custom/libs:.",
        "ANOTHER_VAR": "value"
    },
    "encoding": "utf-8", // Optional: Encoding for stdio communication (default: "utf-8")
    "encoding_error_handler": "strict", // Optional: How to handle encoding errors. Can be "strict", "ignore", or "replace" (default: "strict").
    "disabled": false // Set to true to temporarily disable this server without removing its configuration.
}
```

**2. Remote SSE Server**

```json
{
    "name": "My Remote API Tools",
    "description": "Optional: Description of the remote SSE server.",
    "type": "sse", // Optional: Explicitly specify server type. Can be "stdio", "sse", or streaming HTTP variants ("http-stream", "streaming-http", "streamable-http", "http-streaming"). Auto-detected if omitted.
    "url": "https://api.example.com/mcp-sse-endpoint", // The full URL for the SSE endpoint of the MCP server.
    "headers": { // Optional: Any HTTP headers required for the connection.
        "Authorization": "Bearer YOUR_API_KEY_OR_TOKEN",
        "X-Custom-Header": "some_value"
    },
    "timeout": 5.0, // Optional: Connection timeout in seconds (default: 5.0).
    "sse_read_timeout": 300.0, // Optional: Read timeout for the SSE stream in seconds (default: 300.0, i.e., 5 minutes).
    "disabled": false
}
```

**3. Remote Streaming HTTP Server**

```json
{
    "name": "My Streaming HTTP Tools",
    "description": "Optional: Description of the remote streaming HTTP server.",
    "type": "streaming-http", // Optional: Explicitly specify server type. Can be "stdio", "sse", or streaming HTTP variants ("http-stream", "streaming-http", "streamable-http", "http-streaming"). Auto-detected if omitted.
    "url": "https://api.example.com/mcp-http-endpoint", // The full URL for the streaming HTTP endpoint of the MCP server.
    "headers": { // Optional: Any HTTP headers required for the connection.
        "Authorization": "Bearer YOUR_API_KEY_OR_TOKEN",
        "X-Custom-Header": "some_value"
    },
    "timeout": 5.0, // Optional: Connection timeout in seconds (default: 5.0).
    "sse_read_timeout": 300.0, // Optional: Read timeout for the SSE and streaming HTTP streams in seconds (default: 300.0, i.e., 5 minutes).
    "disabled": false
}
```

**Example `mcp_servers` value in `tmp/settings.json`:**

```json
{
    // ... other settings ...
    "mcp_servers": "[{'name': 'MyPythonTools', 'command': 'python3', 'args': ['mcp_scripts/my_server.py'], 'disabled': false}, {'name': 'ExternalAPI', 'url': 'https://data.example.com/mcp', 'headers': {'X-Auth-Token': 'supersecret'}, 'disabled': false}]",
    // ... other settings ...
}
```

**Key Configuration Fields:**

*   `"name"`: A unique name for the server. This name will be used to prefix the tools provided by this server (e.g., `my_server_name.tool_name`). The name is normalized internally (converted to lowercase, spaces and hyphens replaced with underscores).
*   `"type"`: Optional explicit server type specification. Can be `"stdio"`, `"sse"`, or streaming HTTP variants (`"http-stream"`, `"streaming-http"`, `"streamable-http"`, `"http-streaming"`). If omitted, the type is auto-detected based on the presence of `"command"` (stdio) or `"url"` (defaults to sse for backward compatibility).
*   `"disabled"`: A boolean (`true` or `false`). If `true`, Agent Zero will ignore this server configuration.
*   `"url"`: **Required for Remote SSE and Streaming HTTP Servers.** The endpoint URL.
*   `"command"`: **Required for Local Stdio Servers.** The executable command.
*   `"args"`: Optional list of arguments for local Stdio servers.
*   Other fields are specific to the server type and mostly optional with defaults.

## Using MCP Tools

Once configured, successfully installed (if applicable, e.g., for `npx` based servers), and discovered by Agent Zero:

*   **Tool Naming**: MCP tools will appear to the agent with a name prefixed by the server name you defined (and normalized, e.g., lowercase, underscores for spaces/hyphens). For instance, if your server is named `"sequential-thinking"` in the configuration and it offers a tool named `"run_chain"`, the agent will know it as `sequential_thinking.run_chain`.
*   **Agent Interaction**: You can instruct the agent to use these tools. For example: "Agent, use the `sequential_thinking.run_chain` tool with the following input..." The agent's LLM will then formulate the appropriate JSON request.
*   **Execution Flow**: Agent Zero's `process_tools` method (with logic in `python/helpers/mcp_handler.py`) prioritizes looking up the tool name in the `MCPConfig`. If found, the execution is delegated to the corresponding MCP server. If not found as an MCP tool, it then attempts to find a local/built-in tool with that name.

This setup provides a flexible way to extend Agent Zero's capabilities by integrating with various external tool providers without modifying its core codebase.
