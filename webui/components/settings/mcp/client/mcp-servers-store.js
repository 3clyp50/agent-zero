import { createStore } from "/js/AlpineStore.js";
import sleep from "/js/sleep.js";
import * as API from "/js/api.js";
import { openModal } from "/js/modals.js";
import { store as settingsStore } from "/components/settings/settings-store.js";
import {
  toastFrontendError,
  toastFrontendSuccess,
  toastFrontendWarning,
} from "/components/notifications/notification-store.js";

const EMPTY_CONFIG = '{\n  "mcpServers": {}\n}';
const STATUS_INTERVAL_MS = 3000;

function normalizeName(value) {
  return String(value || "mcp_server")
    .trim()
    .toLowerCase()
    .replace(/[^\w]/gu, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "") || "mcp_server";
}

function parseJsonConfig(value) {
  const text = String(value || "").trim() || EMPTY_CONFIG;
  const parsed = JSON.parse(text);
  if (Array.isArray(parsed)) return { mcpServers: parsed };
  if (parsed && typeof parsed === "object") {
    if (!parsed.mcpServers) parsed.mcpServers = {};
    return parsed;
  }
  return { mcpServers: {} };
}

function stringifyConfig(config) {
  return JSON.stringify(config || { mcpServers: {} }, null, 2);
}

function parseKeyValueText(text) {
  const raw = String(text || "").trim();
  if (!raw) return {};
  if (raw.startsWith("{")) {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  }

  return raw.split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .reduce((acc, line) => {
      const idx = line.indexOf("=");
      if (idx <= 0) return acc;
      const key = line.slice(0, idx).trim();
      if (!key) return acc;
      acc[key] = line.slice(idx + 1).trim();
      return acc;
    }, {});
}

function formatKeyValueText(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return "";
  return Object.entries(value)
    .map(([key, val]) => `${key}=${val ?? ""}`)
    .join("\n");
}

function parseArgsText(text) {
  const raw = String(text || "").trim();
  if (!raw) return [];
  if (raw.startsWith("[")) {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.map((item) => String(item)) : [];
  }
  return raw.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
}

function formatArgsText(value) {
  return Array.isArray(value) ? value.join("\n") : "";
}

function deriveNameFromUrl(url) {
  try {
    const parsed = new URL(url);
    const parts = parsed.pathname.split("/").filter(Boolean);
    return normalizeName(parts.at(-1) || parsed.hostname || "remote_mcp");
  } catch {
    return "remote_mcp";
  }
}

function createEmptyForm() {
  return {
    mode: "remote",
    name: "",
    description: "",
    url: "",
    type: "streamable-http",
    command: "",
    argsText: "",
    headersText: "",
    envText: "",
    init_timeout: "",
    tool_timeout: "",
    verify: true,
    disabled: false,
    allow_local_execution: false,
    allow_remote_network: false,
  };
}

const model = {
  editor: null,
  servers: [],
  loading: true,
  applying: false,
  statusCheck: false,
  serverLog: "",
  serverDetail: null,
  activeView: "visual",
  addOpen: false,
  advancedOpen: false,
  serverForm: createEmptyForm(),
  scanLoading: false,
  scanResult: null,
  scope: "global",
  projectName: "",
  projectModel: null,
  standaloneProject: false,

  async initialize() {
    this.loading = true;
    await this.ensureScopeLoaded();
    this.setupEditor();
    await this.loadStatus();
    this.loading = false;
    this.startStatusCheck();
  },

  setupEditor() {
    const container = document.getElementById("mcp-servers-config-json");
    if (!container) return;

    const editor = ace.edit("mcp-servers-config-json");
    const dark = localStorage.getItem("darkMode");
    editor.setTheme(dark !== "false" ? "ace/theme/github_dark" : "ace/theme/tomorrow");
    editor.session.setMode("ace/mode/json");
    editor.setValue(this.getScopeConfigJson());
    editor.clearSelection();
    this.editor = editor;
    requestAnimationFrame(() => this.editor?.resize());
  },

  async ensureScopeLoaded() {
    if (this.scope === "project") return;
    if (settingsStore.settings) return;

    try {
      const response = await API.callJsonApi("settings_get", null);
      if (response?.settings) {
        settingsStore.settings = response.settings;
        settingsStore.additional = response.additional || null;
      }
    } catch (error) {
      console.error("Failed to load settings for MCP manager:", error);
      void toastFrontendError("Failed to load settings for MCP manager", "MCP Servers");
    }
  },

  async openGlobalConfig() {
    this.configureGlobalScope();
    await openModal("settings/mcp/client/mcp-servers.html");
  },

  async openProjectConfig(projectModel) {
    if (!projectModel?.name) return;
    this.configureProjectScope(projectModel.name, projectModel, false);
    await openModal("settings/mcp/client/mcp-servers.html");
  },

  async openFromComposer(projectName = "") {
    const normalizedProject = String(projectName || "").trim();
    if (normalizedProject) {
      try {
        const response = await API.callJsonApi("projects", {
          action: "load",
          name: normalizedProject,
        });
        if (!response?.ok) throw new Error(response?.error || "Project load failed");
        this.configureProjectScope(normalizedProject, response.data, true);
      } catch (error) {
        console.error("Failed to load project MCP config:", error);
        void toastFrontendError("Failed to load project MCP config", "MCP Servers");
        return;
      }
    } else {
      this.configureGlobalScope();
      await this.ensureScopeLoaded();
    }
    await openModal("settings/mcp/client/mcp-servers.html");
  },

  configureGlobalScope() {
    this.scope = "global";
    this.projectName = "";
    this.projectModel = null;
    this.standaloneProject = false;
  },

  configureProjectScope(projectName, projectModel, standaloneProject = false) {
    this.scope = "project";
    this.projectName = projectName;
    this.projectModel = projectModel || null;
    this.standaloneProject = !!standaloneProject;
  },

  resetScope() {
    this.configureGlobalScope();
  },

  get scopeTitle() {
    if (this.scope === "project") return `Project MCP servers`;
    return "Global MCP servers";
  },

  get scopeSubtitle() {
    if (this.scope === "project") {
      return this.projectName ? `Project: ${this.projectName}` : "Project scope";
    }
    return "Available to every chat unless a project overrides a server.";
  },

  getStatusPayload() {
    return this.scope === "project" && this.projectName
      ? { project_name: this.projectName }
      : null;
  },

  getApplyPayload() {
    const payload = { mcp_servers: this.getEditorValue() };
    if (this.scope === "project" && this.projectName) payload.project_name = this.projectName;
    return payload;
  },

  getScopeConfigJson() {
    if (this.scope === "project") {
      return this.projectModel?.mcp_servers || EMPTY_CONFIG;
    }
    return settingsStore.settings?.mcp_servers
      ?? settingsStore.settings?.mcpServers
      ?? EMPTY_CONFIG;
  },

  setScopeConfigJson(value) {
    if (this.scope === "project") {
      if (this.projectModel) this.projectModel.mcp_servers = value;
      return;
    }
    if (settingsStore.settings) settingsStore.settings.mcp_servers = value;
  },

  getEditorValue() {
    return this.editor?.getValue() ?? this.getScopeConfigJson();
  },

  setEditorValue(value) {
    if (this.editor) {
      this.editor.setValue(value);
      this.editor.clearSelection();
      this.editor.navigateFileStart();
      requestAnimationFrame(() => this.editor?.resize());
    }
    this.setScopeConfigJson(value);
  },

  getConfigObject() {
    return parseJsonConfig(this.getEditorValue());
  },

  get configuredServers() {
    try {
      const config = this.getConfigObject();
      const servers = config.mcpServers;
      if (Array.isArray(servers)) {
        return servers.map((server, index) => ({
          name: server?.name || `server_${index + 1}`,
          config: server || {},
        }));
      }
      if (servers && typeof servers === "object") {
        return Object.entries(servers).map(([name, config]) => ({
          name,
          config: config || {},
        }));
      }
    } catch {
      return [];
    }
    return [];
  },

  countServersInConfig(configText) {
    try {
      const config = parseJsonConfig(configText || EMPTY_CONFIG);
      if (Array.isArray(config.mcpServers)) return config.mcpServers.length;
      return Object.keys(config.mcpServers || {}).length;
    } catch {
      return 0;
    }
  },

  formatJson() {
    try {
      this.setEditorValue(stringifyConfig(this.getConfigObject()));
      void toastFrontendSuccess("MCP JSON reformatted", "MCP Servers");
    } catch (error) {
      console.error("Failed to format JSON:", error);
      void toastFrontendError(`Invalid JSON: ${error.message}`, "MCP Servers");
    }
  },

  setActiveView(view) {
    this.activeView = view || "visual";
    if (this.activeView === "raw") {
      requestAnimationFrame(() => this.editor?.resize());
    }
  },

  setFormMode(mode) {
    this.serverForm.mode = mode === "local" ? "local" : "remote";
    this.scanResult = null;
  },

  resetForm() {
    this.serverForm = createEmptyForm();
    this.advancedOpen = false;
    this.scanResult = null;
  },

  buildServerFromForm() {
    const form = this.serverForm;
    const name = normalizeName(form.name || (form.mode === "remote" ? deriveNameFromUrl(form.url) : form.command));
    if (!name) throw new Error("Name is required");

    const server = {
      name,
      disabled: !!form.disabled,
    };

    if (form.description.trim()) server.description = form.description.trim();

    if (form.init_timeout !== "" && form.init_timeout !== null) {
      const timeout = Number(form.init_timeout);
      if (Number.isFinite(timeout) && timeout > 0) server.init_timeout = timeout;
    }
    if (form.tool_timeout !== "" && form.tool_timeout !== null) {
      const timeout = Number(form.tool_timeout);
      if (Number.isFinite(timeout) && timeout > 0) server.tool_timeout = timeout;
    }

    if (form.mode === "remote") {
      if (!form.url.trim()) throw new Error("Remote MCP server URL is required");
      server.url = form.url.trim();
      server.type = form.type || "streamable-http";
      server.verify = form.verify !== false;
      const headers = parseKeyValueText(form.headersText);
      if (Object.keys(headers).length) server.headers = headers;
    } else {
      if (!form.command.trim()) throw new Error("Local command is required");
      server.type = "stdio";
      server.command = form.command.trim();
      const args = parseArgsText(form.argsText);
      if (args.length) server.args = args;
      const env = parseKeyValueText(form.envText);
      if (Object.keys(env).length) server.env = env;
    }

    return server;
  },

  async scanForm() {
    let server;
    try {
      server = this.buildServerFromForm();
    } catch (error) {
      void toastFrontendError(error.message || String(error), "MCP Scanner");
      return;
    }

    this.scanLoading = true;
    this.scanResult = null;
    try {
      const response = await API.callJsonApi("mcp_server_scan", {
        server,
        inspect_runtime: true,
        allow_local_execution: !!this.serverForm.allow_local_execution,
        allow_remote_network: !!this.serverForm.allow_remote_network,
      });
      if (!response?.success) throw new Error(response?.error || "Scan failed");
      this.scanResult = response;
    } catch (error) {
      console.error("MCP scan failed:", error);
      void toastFrontendError(`MCP scan failed: ${error.message || error}`, "MCP Scanner");
    } finally {
      this.scanLoading = false;
    }
  },

  addServerFromForm() {
    let server;
    try {
      server = this.buildServerFromForm();
    } catch (error) {
      void toastFrontendError(error.message || String(error), "MCP Servers");
      return;
    }

    try {
      const config = this.getConfigObject();
      if (Array.isArray(config.mcpServers)) {
        const index = config.mcpServers.findIndex((item) => normalizeName(item?.name || "") === server.name);
        if (index >= 0) config.mcpServers.splice(index, 1, server);
        else config.mcpServers.push(server);
      } else {
        const stored = { ...server };
        delete stored.name;
        config.mcpServers[server.name] = stored;
      }
      this.setEditorValue(stringifyConfig(config));
      this.addOpen = false;
      this.resetForm();
      void toastFrontendSuccess("MCP server added to draft config", "MCP Servers");
    } catch (error) {
      console.error("Failed to add MCP server:", error);
      void toastFrontendError(`Failed to add MCP server: ${error.message || error}`, "MCP Servers");
    }
  },

  editConfigServer(name) {
    const entry = this.configuredServers.find((item) => item.name === name);
    if (!entry) return;
    const cfg = entry.config || {};
    const isRemote = !!(cfg.url || cfg.serverUrl);
    this.serverForm = {
      ...createEmptyForm(),
      mode: isRemote ? "remote" : "local",
      name,
      description: cfg.description || "",
      url: cfg.url || cfg.serverUrl || "",
      type: cfg.type || "streamable-http",
      command: cfg.command || "",
      argsText: formatArgsText(cfg.args),
      headersText: formatKeyValueText(cfg.headers),
      envText: formatKeyValueText(cfg.env),
      init_timeout: cfg.init_timeout || "",
      tool_timeout: cfg.tool_timeout || "",
      verify: cfg.verify !== false,
      disabled: !!cfg.disabled,
      allow_local_execution: false,
      allow_remote_network: false,
    };
    this.addOpen = true;
    this.scanResult = null;
  },

  removeConfigServer(name) {
    try {
      const config = this.getConfigObject();
      if (Array.isArray(config.mcpServers)) {
        config.mcpServers = config.mcpServers.filter((server) => normalizeName(server?.name || "") !== normalizeName(name));
      } else {
        delete config.mcpServers[name];
      }
      this.setEditorValue(stringifyConfig(config));
    } catch (error) {
      void toastFrontendError(`Failed to remove MCP server: ${error.message || error}`, "MCP Servers");
    }
  },

  toggleConfigServer(name) {
    try {
      const config = this.getConfigObject();
      if (Array.isArray(config.mcpServers)) {
        const server = config.mcpServers.find((item) => normalizeName(item?.name || "") === normalizeName(name));
        if (server) server.disabled = !server.disabled;
      } else if (config.mcpServers[name]) {
        config.mcpServers[name].disabled = !config.mcpServers[name].disabled;
      }
      this.setEditorValue(stringifyConfig(config));
    } catch (error) {
      void toastFrontendError(`Failed to update MCP server: ${error.message || error}`, "MCP Servers");
    }
  },

  async startStatusCheck() {
    this.statusCheck = true;
    while (this.statusCheck) {
      await sleep(STATUS_INTERVAL_MS);
      if (this.statusCheck) await this.loadStatus({ silent: true });
    }
  },

  async loadStatus(options = {}) {
    try {
      const resp = await API.callJsonApi("mcp_servers_status", this.getStatusPayload());
      if (resp?.success) {
        this.servers = resp.status || [];
        this.servers.sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")));
      } else if (!options.silent) {
        void toastFrontendWarning(resp?.error || "Unable to load MCP status", "MCP Servers");
      }
    } catch (error) {
      if (!options.silent) {
        console.error("Failed to load MCP status:", error);
        void toastFrontendError("Failed to load MCP status", "MCP Servers");
      }
    }
  },

  stopStatusCheck() {
    this.statusCheck = false;
  },

  async applyNow() {
    if (this.applying) return;
    try {
      const formatted = stringifyConfig(this.getConfigObject());
      this.setEditorValue(formatted);
    } catch (error) {
      void toastFrontendError(`Invalid JSON: ${error.message || error}`, "MCP Servers");
      return;
    }

    this.applying = true;
    try {
      const resp = await API.callJsonApi("mcp_servers_apply", this.getApplyPayload());
      if (!resp?.success) throw new Error(resp?.error || "Apply failed");
      this.setScopeConfigJson(resp.mcp_servers || this.getEditorValue());
      this.servers = resp.status || [];
      this.servers.sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")));
      void toastFrontendSuccess("MCP servers applied", "MCP Servers");
      await sleep(100);
      if (globalThis.scrollModal) globalThis.scrollModal("mcp-servers-status");
    } catch (error) {
      console.error("Failed to apply MCP servers:", error);
      void toastFrontendError(`Failed to apply MCP servers: ${error.message || error}`, "MCP Servers");
    } finally {
      this.applying = false;
    }
  },

  async getServerLog(serverName) {
    this.serverLog = "";
    const payload = { server_name: serverName, ...(this.getStatusPayload() || {}) };
    const resp = await API.callJsonApi("mcp_server_get_log", payload);
    if (resp?.success) {
      this.serverLog = resp.log;
      openModal("settings/mcp/client/mcp-servers-log.html");
    }
  },

  async onToolCountClick(serverName) {
    const payload = { server_name: serverName, ...(this.getStatusPayload() || {}) };
    const resp = await API.callJsonApi("mcp_server_get_detail", payload);
    if (resp?.success) {
      this.serverDetail = resp.detail;
      openModal("settings/mcp/client/mcp-server-tools.html");
    }
  },

  statusLabel(server) {
    if (!server.connected) return "Unavailable";
    if (server.error) return "Needs attention";
    if ((server.tool_count || 0) > 0) return "Ready";
    return "Connected";
  },

  statusClass(server) {
    if (!server.connected || server.error) return "danger";
    if ((server.tool_count || 0) > 0) return "ok";
    return "idle";
  },

  configModeLabel(config) {
    if (config?.disabled) return "Disabled";
    if (config?.url || config?.serverUrl) return "Remote";
    return "Local";
  },

  configSummary(config) {
    if (config?.url || config?.serverUrl) return config.url || config.serverUrl;
    const args = Array.isArray(config?.args) && config.args.length ? ` ${config.args.join(" ")}` : "";
    return `${config?.command || "command"}${args}`;
  },

  get scanWarnings() {
    return this.scanResult?.warnings || [];
  },

  get scanRiskLabel() {
    const risk = this.scanResult?.risk_level || "";
    if (risk === "ok") return "No major issues found";
    if (risk === "warning") return "Review warnings";
    if (risk === "error") return "Action needed";
    return "";
  },

  onClose() {
    try {
      this.setScopeConfigJson(this.getEditorValue());
    } catch {}
    this.stopStatusCheck();
    if (this.editor) {
      try { this.editor.destroy(); } catch {}
      this.editor = null;
    }
    this.servers = [];
    this.loading = true;
    this.applying = false;
    this.addOpen = false;
    this.activeView = "visual";
    this.resetForm();
    this.resetScope();
  },
};

const store = createStore("mcpServersStore", model);

export { store };
