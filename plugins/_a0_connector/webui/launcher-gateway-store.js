import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";
import { toastFrontendError } from "/components/notifications/notification-store.js";

const STATUS_API = "/plugins/_a0_connector/v1/launcher_gateway_status";
const CONTROL_API = "/plugins/_a0_connector/v1/launcher_gateway_control";

const model = {
  status: { state: "disconnected", gateway: null },
  loading: false,
  saving: false,
  open: false,
  intervalId: null,
  reconnectAvailable: false,

  get visible() {
    return /(?:^|\s)A0-Launcher\/[^\s]+/.test(navigator.userAgent);
  },

  get canReconnect() {
    return typeof window.a0LauncherHost?.reconnect === "function";
  },

  get gateway() {
    return this.state === "disconnected" ? null : this.status?.gateway || null;
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
      await this.refreshReconnectState();
    }
  },

  async refreshReconnectState() {
    try {
      const state = await window.a0LauncherHost?.getState?.();
      this.reconnectAvailable = state?.reconnectAvailable === true;
    } catch {
      this.reconnectAvailable = false;
    }
  },

  async setMaster(enabled) {
    await this.control({ action: "set_master", enabled: Boolean(enabled) });
  },

  async setScope(scope, enabled) {
    const current = this.gateway?.scopes || {};
    const scopes = {
      files: Boolean(current.files),
      file_write: Boolean(current.file_write ?? current.files),
      code_execution: Boolean(current.code_execution),
      browser: Boolean(current.browser),
      computer_use: Boolean(current.computer_use),
      [scope]: Boolean(enabled),
    };
    if (!scopes.files) scopes.file_write = false;
    if (!scopes.file_write) scopes.code_execution = false;
    return this.control({ action: "replace_scopes", scopes });
  },

  async setComputerUse(enabled) {
    if (!this.gateway) await this.refresh();
    if (!this.gateway) throw new Error("Launcher Host access is not connected.");
    if (!this.gateway.master_enabled) {
      throw new Error("Launcher Host access is paused. Resume it first.");
    }

    const requested = Boolean(enabled);
    if (requested && typeof window.a0LauncherHost?.rearmComputerUse !== "function") {
      throw new Error(
        "This A0 Launcher cannot request Computer Use permission. Update it or use A0 CLI.",
      );
    }
    if (Boolean(this.gateway.scopes?.computer_use) !== requested) {
      if (!await this.setScope("computer_use", requested)) return false;
    }
    if (!requested) return true;

    const response = await window.a0LauncherHost.rearmComputerUse();
    if (!response?.ok) {
      throw new Error(
        response?.message || "Computer Use permission could not be requested.",
      );
    }
    return true;
  },

  async emergencyDisconnect() {
    if (await this.control({ action: "emergency_disconnect" })) {
      this.reconnectAvailable = this.canReconnect;
      this.status = { ...this.status, state: "disconnected", connected: false, gateway: null, gateways: [] };
      if (!this.canReconnect) this.open = false;
    }
  },

  async reconnect() {
    if (this.saving) return;
    this.saving = true;
    try {
      const response = await window.a0LauncherHost?.reconnect?.();
      if (!response?.ok) throw new Error(response?.message || "Host access could not reconnect.");
      this.reconnectAvailable = false;
      this.status = { ...this.status, state: "connecting", connected: false, gateway: null, gateways: [] };
    } catch (error) {
      console.error("Failed to reconnect Launcher host:", error);
      void toastFrontendError(
        error?.message || "Host access could not reconnect.",
        "Host access",
      );
      await this.refreshReconnectState();
    } finally {
      this.saving = false;
    }
  },

  async control(payload) {
    if (this.saving) return;
    this.saving = true;
    try {
      const response = await callJsonApi(CONTROL_API, payload);
      this.status = response?.status || this.status;
      return true;
    } catch (error) {
      console.error("Failed to control Launcher host:", error);
      void toastFrontendError(
        error?.message || "Host access change failed.",
        "Host access",
      );
      await this.refresh();
      return false;
    } finally {
      this.saving = false;
    }
  },
};

export const store = createStore("launcherGateway", model);
