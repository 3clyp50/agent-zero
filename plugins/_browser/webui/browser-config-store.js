import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

const BROWSER_STATUS_API = "/plugins/_browser/status";
const RUNTIME_BACKENDS = new Set(["container", "host_required"]);
const HOST_PRIVACY_POLICIES = new Set(["enforce_local", "warn", "allow"]);
const HOST_PROFILE_MODES = new Set(["existing", "agent"]);

function ensureConfig(config) {
  if (!config || typeof config !== "object") return null;
  config.default_homepage = String(config.default_homepage || "about:blank").trim() || "about:blank";
  config.autofocus_active_page = normalizeBoolean(config.autofocus_active_page, true);
  config.runtime_backend = normalizeRuntimeBackend(config.runtime_backend);
  config.host_browser_privacy_policy = normalizeChoice(
    config.host_browser_privacy_policy,
    HOST_PRIVACY_POLICIES,
    "allow",
  );
  config.host_browser_profile_mode = normalizeChoice(
    config.host_browser_profile_mode,
    HOST_PROFILE_MODES,
    "existing",
  );
  config.model_preset = String(config.model_preset || "").trim();
  delete config.model;
  return config;
}

function normalizeChoice(value, allowed, fallback) {
  const normalized = String(value || "").trim().toLowerCase().replace(/-/g, "_");
  return allowed.has(normalized) ? normalized : fallback;
}

function normalizeRuntimeBackend(value) {
  const normalized = String(value || "").trim().toLowerCase().replace(/-/g, "_");
  if (normalized === "host_when_available") return "host_required";
  return RUNTIME_BACKENDS.has(normalized) ? normalized : "container";
}

function normalizeBoolean(value, fallback = true) {
  if (value === undefined || value === null || value === "") return fallback;
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return Boolean(value);
  const normalized = String(value).trim().toLowerCase();
  if (["1", "true", "yes", "on", "enabled"].includes(normalized)) return true;
  if (["0", "false", "no", "off", "disabled"].includes(normalized)) return false;
  return fallback;
}

function hostBrowserFamilyLabel(value) {
  const family = String(value || "").trim().toLowerCase();
  const a0Profile = family.endsWith("-a0");
  const remoteDebugging = family.endsWith("-cdp");
  const base = a0Profile ? family.slice(0, -3) : remoteDebugging ? family.slice(0, -4) : family;
  const labels = {
    chrome: "Chrome",
    chromium: "Chromium",
    edge: "Edge",
    "edge-dev": "Edge Dev",
  };
  const label = labels[base] || "Host browser";
  if (remoteDebugging) return `${label} (allowed)`;
  return a0Profile ? `${label} (A0 profile)` : label;
}

function hostBrowserStatusLabel(value) {
  const status = String(value || "").trim().toLowerCase();
  if (status === "active") return "open";
  if (status === "ready") return "ready";
  if (status === "disabled") return "will open on first use";
  if (status === "relaunch_required") return "close browser and retry";
  if (status === "unsupported") return "unavailable";
  return status || "ready";
}

export const store = createStore("browserConfig", {
  config: null,
  hostBrowserStatus: null,
  hostBrowserStatusLoading: false,

  async init(config) {
    this.bindConfig(config);
    await this.loadHostBrowserStatus();
  },

  cleanup() {
    this.config = null;
    this.hostBrowserStatus = null;
    this.hostBrowserStatusLoading = false;
  },

  bindConfig(config) {
    const safeConfig = ensureConfig(config);
    if (!safeConfig) return;
    if (this.config === safeConfig) return;
    this.config = safeConfig;
  },

  setAutofocusActivePage(enabled) {
    const safeConfig = ensureConfig(this.config);
    if (!safeConfig) return;
    safeConfig.autofocus_active_page = Boolean(enabled);
  },

  autofocusLabel() {
    return this.config?.autofocus_active_page === false ? "Off" : "On";
  },

  runtimeBackendLabel() {
    const value = this.config?.runtime_backend || "container";
    if (value === "host_required") return "Bring Your Own Browser";
    return "Docker Browser";
  },

  privacyPolicyLabel() {
    const value = this.config?.host_browser_privacy_policy || "allow";
    if (value === "warn") return "Warn When Using Cloud";
    if (value === "allow") return "Allow";
    return "Local Models Only";
  },

  hostBrowserProfileModeLabel() {
    const value = this.config?.host_browser_profile_mode || "existing";
    if (value === "agent") return "Clean Agent Profile";
    return "Existing Browser Profile";
  },

  async loadHostBrowserStatus() {
    if (this.hostBrowserStatusLoading) return;
    this.hostBrowserStatusLoading = true;
    try {
      const response = await callJsonApi(BROWSER_STATUS_API, {});
      this.hostBrowserStatus = response?.host_browser || { connectors: [] };
    } catch (_error) {
      this.hostBrowserStatus = { connectors: [] };
    } finally {
      this.hostBrowserStatusLoading = false;
    }
  },

  hostBrowserConnectorLabel() {
    const connectors = Array.isArray(this.hostBrowserStatus?.connectors)
      ? this.hostBrowserStatus.connectors
      : [];
    const active = connectors.find((item) => item?.supported && item?.enabled);
    if (active) {
      const profile = active.profile_label ? ` - ${active.profile_label}` : "";
      return `${hostBrowserFamilyLabel(active.browser_family)}${profile}: ${hostBrowserStatusLabel(active.status)}`;
    }
    const preparable = connectors.find((item) => item?.can_prepare || item?.supported);
    if (preparable) return "A0 CLI connected - browser will open on first use";
    if (connectors.length) return "A0 CLI connected - host browser unavailable";
    return "Connect A0 CLI to use a host browser";
  },

  browserRuntimeStatusLabel() {
    if (this.config?.runtime_backend !== "host_required") {
      return "Docker browser runs as CDP-controlled Chromium inside Agent Zero; A0 CLI host-browser status does not affect it.";
    }
    const label = this.hostBrowserConnectorLabel();
    if (label.startsWith("Connect A0 CLI") || label.includes("unavailable")) {
      return `${label}. Switch Browser location to Internal Docker browser to browse without A0 CLI.`;
    }
    return label;
  },
});
