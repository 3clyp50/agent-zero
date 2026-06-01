# MCP Setup

MCP lets Agent Zero use tools from other apps and services.

Think of each MCP connection as a bridge. One bridge might connect Gmail,
another might connect a database, and another might connect an automation app.

Use MCP when you have a clear external tool you want Agent Zero to call. For
normal browsing, start with Agent Zero's built-in Browser first.

> [!NOTE]
> This page is about giving Agent Zero tools from other apps. For deeper MCP
> details, see the [advanced MCP reference](../developer/mcp-configuration.md).

## When To Use MCP

| Need | Good first stop |
| --- | --- |
| Browse, screenshot, annotate, or use the Docker browser | [Browser Guide](browser.md) |
| Use your host Chrome-family browser through A0 CLI | [A0 CLI Connector](a0-cli-connector.md#host-browser) |
| Connect a third-party app or service with MCP support | This guide |
| Paste or review MCP JSON by hand | [Advanced MCP Configuration](../developer/mcp-configuration.md) |

## Before You Add One

- [ ] You know what app or service you want to connect.
- [ ] You trust the package or URL.
- [ ] You know where it will run: inside Agent Zero, on your computer, or online.
- [ ] You have any needed credentials ready.
- [ ] You know whether the tool should be project-specific or global.

## Open MCP Settings

1. Click **Settings** in the sidebar.
2. Open the **MCP/A2A** tab.
3. Find **External MCP Servers**.
4. Click **Open**.

![MCP Configuration Access](../res/setup/mcp/mcp-open-config.png)

## Add A Connection

The configuration editor accepts JSON. A command-based MCP connection looks like
this:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

![MCP Configuration Example](../res/setup/mcp/mcp-example-config.png)

Click **Apply now** after editing.

> [!TIP]
> The first launch of an `npx` or `uvx` server can take a little longer because
> the package may need to download.

## Check That It Connected

After applying the config, look for the status below the editor.

| Signal | What it means |
| --- | --- |
| Name | The connection Agent Zero found. |
| Tool count | How many tools are available. |
| Green status | The connection is working. |
| Error text | The command, URL, network, or credentials need attention. |

MCP tools become available automatically after the connection works.

You can still ask naturally:

```text
Use the connected Gmail tools to find the last message from Alice and summarize it.
```

## Common Examples

### Tool Started By A Command

Use this pattern when Agent Zero should start the tool itself.

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "/root/db.sqlite"]
    }
  }
}
```

### Tool At A URL

Use this pattern when the tool is already running at a URL.

```json
{
  "mcpServers": {
    "external-api": {
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

> [!IMPORTANT]
> Do not paste real API keys into public files, screenshots, or issue reports.
> Prefer project secrets or environment variables when possible.

## Docker Networking

If Agent Zero runs in Docker and the MCP tool runs somewhere else, the address
matters.

| Where the MCP tool runs | What to use from Agent Zero |
| --- | --- |
| Host machine on macOS or Windows | `host.docker.internal` |
| Another container | Same Docker network plus the container name |
| Remote server | The reachable HTTPS URL |
| Inside Agent Zero's container | Local command config |

On Linux, `host.docker.internal` is not always available by default. Running the
MCP tool in the same Docker network is usually cleaner.

## Browser MCP Or Built-In Browser?

For most browsing tasks, use Agent Zero's built-in `_browser` plugin and direct
`browser` tool. It covers the Docker browser surface, screenshots, annotations,
and optional A0 CLI host-browser mode.

MCP-based browser tools are still useful when another browser tool is required
for a specific workflow.

See the [Browser Guide](browser.md) for the built-in workflow.

## Recommended Server Types

| Tool type | Useful for |
| --- | --- |
| Chrome DevTools MCP | Direct Chrome debugging/control workflows |
| Playwright MCP | Alternative browser automation stacks |
| n8n MCP | Workflow automation |
| Gmail MCP | Email workflows |
| VS Code MCP | IDE-centered workflows |

## Troubleshooting

- **No tools appear:** confirm the JSON is valid and click **Apply now** again.
- **Command not found:** install the command where Agent Zero can run it, or use a URL-based tool instead.
- **Package launch is slow:** wait for the first package download to finish.
- **Host service unreachable:** check Docker networking and try `host.docker.internal` on macOS or Windows.
- **Credentials fail:** rotate or re-enter the credential, then restart or reapply the config.

## Related

- [Browser Guide](browser.md): built-in browsing, screenshots, annotations, Docker browser, and host-browser mode.
- [A0 CLI Connector](a0-cli-connector.md): host-machine access and Bring Your Own Browser setup.
- [Advanced MCP Configuration](../developer/mcp-configuration.md): complete configuration reference.
