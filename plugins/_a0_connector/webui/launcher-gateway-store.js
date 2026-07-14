import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

const STATUS_API = "/plugins/_a0_connector/v1/launcher_gateway_status";
const CONTROL_API = "/plugins/_a0_connector/v1/launcher_gateway_control";

const model = {
  status: { state: "disconnected", gateway: null },
  loading: false,
  saving: false,
  open: false,
  intervalId: null,

  get visible() {
    return /(?:^|\s)A0-Launcher\/[^\s]+/.test(navigator.userAgent);
  },

  get gateway() {
    return this.status?.gateway || null;
  },

  get state() {
    return this.status?.state || "disconnected";
  },

  get stateLabel() {
    const labels = {
      connecting: "Connecting",
      connected: "Connected",
      paused: "Paused",
      needs_action: "Needs action",
      error: "Error",
      multiple_hosts: "Multiple hosts",
      disconnected: "Disconnected",
    };
    return labels[this.state] || "Disconnected";
  },

  get stateIcon() {
    const icons = {
      connecting: "sync",
      connected: "computer",
      paused: "pause_circle",
      needs_action: "warning",
      error: "error",
      multiple_hosts: "devices",
      disconnected: "computer_off",
    };
    return icons[this.state] || "computer_off";
  },

  get hostLabel() {
    return this.gateway?.host_label || "Launcher host";
  },

  get preparationMessages() {
    const status = this.gateway?.status || {};
    const messages = [];
    for (const key of ["browser", "computer_use"]) {
      const value = status[key];
      if (typeof value === "string" && value) messages.push(value);
      else if (value?.message) messages.push(value.message);
      else if (value?.error) messages.push(value.error);
    }
    if (this.status?.error) messages.push(this.status.error);
    return [...new Set(messages)];
  },

  onMount() {
    if (!this.visible || this.intervalId) return;
    void this.refresh();
    this.intervalId = window.setInterval(() => this.refresh(), 2000);
  },

  cleanup() {
    if (this.intervalId) window.clearInterval(this.intervalId);
    this.intervalId = null;
  },

  async refresh() {
    if (!this.visible || this.loading) return;
    this.loading = true;
    try {
      this.status = await callJsonApi(STATUS_API, {});
    } catch (error) {
      console.error("Failed to load Launcher host status:", error);
      this.status = { state: "error", gateway: null, error: error?.message || "Status unavailable" };
    } finally {
      this.loading = false;
    }
  },

  async setMaster(enabled) {
    await this.control({ action: "set_master", enabled: Boolean(enabled) });
  },

  async setScope(scope, enabled) {
    const current = this.gateway?.scopes || {};
    const scopes = {
      files: Boolean(current.files),
      code_execution: Boolean(current.code_execution),
      browser: Boolean(current.browser),
      computer_use: Boolean(current.computer_use),
      [scope]: Boolean(enabled),
    };
    if (!scopes.files) scopes.code_execution = false;
    await this.control({ action: "replace_scopes", scopes });
  },

  async emergencyDisconnect() {
    await this.control({ action: "emergency_disconnect" });
    this.open = false;
  },

  async control(payload) {
    if (this.saving) return;
    this.saving = true;
    try {
      const response = await callJsonApi(CONTROL_API, payload);
      this.status = response?.status || this.status;
    } catch (error) {
      console.error("Failed to control Launcher host:", error);
      await this.refresh();
    } finally {
      this.saving = false;
    }
  },
};

export const store = createStore("launcherGateway", model);
