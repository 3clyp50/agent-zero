import { createStore } from "/js/AlpineStore.js";
import { store as modelConfigStore } from "/plugins/_model_config/webui/model-config-store.js";
import { store as chatsStore } from "/components/sidebar/chats/chats-store.js";

const fetchApi = globalThis.fetchApi;

export const store = createStore("onboarding", {
    step: 1,
    config: null,
    loading: true,

    async init() {
        this.step = 1;
        this.loading = true;
        this.config = null;
    },

    async onOpen() {
        await this.init();
        await modelConfigStore.ensureLoaded();
        modelConfigStore.resetApiKeyDrafts();
        await modelConfigStore.refreshApiKeyStatus();
        
        // Fetch current config
        const response = await fetchApi("/plugins", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                action: "get_config",
                plugin_name: "_model_config",
                project_name: "",
                agent_profile: "",
            }),
        });
        const result = await response.json().catch(() => ({}));
        this.config = result.ok ? (result.data || {}) : {};
        
        // Ensure slots exist
        if (!this.config.chat_model) this.config.chat_model = { provider: "", name: "", api_key: "" };
        if (!this.config.utility_model) this.config.utility_model = { provider: "", name: "", api_key: "" };
        
        modelConfigStore.initConfigFields(this.config);
        
        this.loading = false;
    },

    cleanup() {
        this.step = 1;
        this.config = null;
        this.loading = true;
    },

    prev() {
        if (this.step > 1) {
            this.step--;
        }
    },

    next() {
        if (this.step < 3) {
            this.step++;
        }
    },

    async finish() {
        this.loading = true;
        try {
            // Save model config
            await fetchApi("/plugins", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action: "save_config",
                    plugin_name: "_model_config",
                    project_name: "",
                    agent_profile: "",
                    settings: this.config,
                }),
            });
            
            // Save API keys
            await modelConfigStore.persistApiKeysForConfig(this.config);
            
            // Open a new chat after finishing
            window.closeModal?.();
            chatsStore.newChat();
        } catch (e) {
            console.error("Failed to finish onboarding", e);
            globalThis.justToast?.("Failed to save settings", "error");
        } finally {
            this.loading = false;
        }
    },
    
    async openAdvancedSettings() {
        window.closeModal?.();
        // Dynamic import since we just removed the static import to fix cyclic imports
        const { store: pluginSettingsStore } = await import("/components/plugins/plugin-settings-store.js");
        await pluginSettingsStore.openConfig("_model_config");
    }
});