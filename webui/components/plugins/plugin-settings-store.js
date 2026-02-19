import { createStore } from "/js/AlpineStore.js";

const fetchApi = globalThis.fetchApi;

const model = {
    // which plugin this modal is showing
    pluginName: null,
    pluginMeta: null,

    // context selectors (mirrors skills list pattern)
    projects: [],
    agentProfiles: [],
    projectName: "",
    agentProfileKey: "",

    // plugin settings data (plugins bind their fields here)
    settings: {},

    // 'plugin' = save to plugin settings API
    // 'core'   = save via $store.settings.saveSettings() (for plugins that surface core settings)
    saveMode: 'plugin',

    isLoading: false,
    isSaving: false,
    error: null,

    // Called by the subsection button before openModal()
    async open(pluginName) {
        this.pluginName = pluginName;
        this.pluginMeta = null;
        this.settings = {};
        this.error = null;
        this.saveMode = 'plugin';
        this.projectName = "";
        this.agentProfileKey = "";
        await Promise.all([this.loadProjects(), this.loadAgentProfiles()]);
        await this.loadSettings();
    },

    // Called by x-create inside the modal on every open
    async onModalOpen() {
        if (this.pluginName) await this.loadSettings();
    },

    async loadAgentProfiles() {
        try {
            const response = await fetchApi("/agents", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "list" }),
            });
            const data = await response.json().catch(() => ({}));
            this.agentProfiles = data.ok ? (data.data || []) : [];
        } catch {
            this.agentProfiles = [];
        }
    },

    async loadProjects() {
        try {
            const response = await fetchApi("/projects", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "list_options" }),
            });
            const data = await response.json().catch(() => ({}));
            this.projects = data.ok ? (data.data || []) : [];
        } catch {
            this.projects = [];
        }
    },

    async loadSettings() {
        if (!this.pluginName) return;
        this.isLoading = true;
        this.error = null;
        try {
            const response = await fetchApi("/plugins", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action: "get_settings",
                    plugin_name: this.pluginName,
                    project_name: this.projectName || "",
                    agent_profile: this.agentProfileKey || "",
                }),
            });
            const result = await response.json().catch(() => ({}));
            this.settings = result.ok ? (result.data || {}) : {};
            if (!result.ok) this.error = result.error || "Failed to load settings";
        } catch (e) {
            this.error = e?.message || "Failed to load settings";
            this.settings = {};
        } finally {
            this.isLoading = false;
        }
    },

    async save() {
        if (!this.pluginName) return;

        // Core-backed plugins (e.g. memory) delegate to the settings store
        if (this.saveMode === 'core') {
            const coreStore = Alpine.store('settings');
            if (coreStore?.saveSettings) {
                const ok = await coreStore.saveSettings();
                if (ok) window.closeModal?.();
            }
            return;
        }

        // Plugin-specific settings: persist to plugin settings API
        this.isSaving = true;
        this.error = null;
        try {
            const response = await fetchApi("/plugins", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action: "save_settings",
                    plugin_name: this.pluginName,
                    project_name: this.projectName || "",
                    agent_profile: this.agentProfileKey || "",
                    settings: this.settings,
                }),
            });
            const result = await response.json().catch(() => ({}));
            if (!result.ok) this.error = result.error || "Save failed";
            else window.closeModal?.();
        } catch (e) {
            this.error = e?.message || "Save failed";
        } finally {
            this.isSaving = false;
        }
    },

    cleanup() {
        this.pluginName = null;
        this.pluginMeta = null;
        this.settings = {};
        this.error = null;
    },

    // Reactive URL for the plugin's settings component (used with x-html injection)
    get settingsComponentHtml() {
        if (!this.pluginName) return "";
        return `<x-component path="/plugins/${this.pluginName}/webui/settings.html"></x-component>`;
    },
};

export const store = createStore("pluginSettings", model);
