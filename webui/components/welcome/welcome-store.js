import { createStore } from "/js/AlpineStore.js";
import * as API from "/js/api.js";
import { getContext } from "/index.js";
import { store as chatsStore } from "/components/sidebar/chats/chats-store.js";
import { store as memoryStore } from "/components/modals/memory/memory-dashboard-store.js";
import { store as projectsStore } from "/components/projects/projects-store.js";
import { store as settingsStore } from "/components/settings/settings-store.js";
import {
  store as bannerStore,
  BANNER_TYPES,
  BANNER_PRIORITY,
} from "/components/banners/banner-store.js";

const LOCAL_PROVIDER_IDS = new Set(["ollama", "lm_studio", "lmstudio"]);

const isLoopbackHost = (hostname) => {
  if (!hostname) return false;
  const normalized = hostname.toLowerCase();
  if (
    normalized === "localhost" ||
    normalized === "::1" ||
    normalized === "0.0.0.0" ||
    normalized.endsWith(".localhost")
  ) {
    return true;
  }
  if (/^127(?:\.\d{1,3}){3}$/.test(normalized)) {
    return true;
  }
  return false;
};

const normalizeProviderId = (provider) =>
  provider ? provider.toLowerCase().replace(/\s+/g, "_") : "";

const isLocalProvider = (provider) =>
  LOCAL_PROVIDER_IDS.has(normalizeProviderId(provider));

const registerWelcomeBannerChecks = (() => {
  let registered = false;
  return () => {
    if (registered) return;
    registered = true;

    bannerStore.registerCheck("welcome", ({ context, settings }) => {
      const isLocal = isLoopbackHost(context?.hostname);
      const hasCredentials = Boolean(
        settings?.auth_login && settings?.auth_password
      );
      if (isLocal || hasCredentials) return [];
      return [
        bannerStore.createBanner({
          id: "welcome-unsecured-connection",
          title: "Unsecured connection",
          type: BANNER_TYPES.WARNING,
          priority: BANNER_PRIORITY.HIGH,
          html: `
            <p>
              This instance is reachable from a non-local address without authentication.
              Add credentials to protect access from the internet.
            </p>
          `,
          actions: [
            {
              label: "Configure credentials",
              action: "openSettingsTab",
              args: ["external"],
            },
          ],
        }),
      ];
    });

    bannerStore.registerCheck("welcome", ({ context, settings }) => {
      const isLocal = isLoopbackHost(context?.hostname);
      const hasCredentials = Boolean(
        settings?.auth_login && settings?.auth_password
      );
      if (!hasCredentials || isLocal || context?.protocol === "https") return [];
      return [
        bannerStore.createBanner({
          id: "welcome-credentials-plaintext",
          title: "Credentials may be sent unencrypted",
          type: BANNER_TYPES.WARNING,
          priority: BANNER_PRIORITY.MEDIUM,
          html: `
            <p>
              Authentication is enabled but this connection is not using HTTPS.
              Credentials could be intercepted on the network.
            </p>
          `,
        }),
      ];
    });

    bannerStore.registerCheck("welcome", ({ settings }) => {
      const selectedProvider = settings?.chat_model_provider;
      const apiKeyValue = selectedProvider
        ? settings?.api_keys?.[selectedProvider]
        : "";
      if (!selectedProvider || isLocalProvider(selectedProvider) || apiKeyValue) {
        return [];
      }
      return [
        bannerStore.createBanner({
          id: "welcome-missing-api-key",
          title: "Missing API key",
          type: BANNER_TYPES.ERROR,
          priority: BANNER_PRIORITY.HIGH,
          html: `
            <p>
              The selected provider does not have an API key configured.
              Agent Zero will not be able to run until one is added.
            </p>
          `,
          actions: [
            {
              label: "Add API key",
              action: "openSettingsTab",
              args: ["external"],
            },
          ],
        }),
      ];
    });
  };
})();

const model = {
  // State
  isVisible: true,
  banners: [],
  bannerChecksInFlight: false,

  init() {
    registerWelcomeBannerChecks();
    // Initialize visibility based on current context
    this.updateVisibility();
    if (this.isVisible) {
      this.refreshBanners();
    }

    // Watch for context changes with faster polling
    let lastSettings = settingsStore.settings;

    setInterval(() => {
      const wasVisible = this.isVisible;
      this.updateVisibility();
      
      // Check if settings have changed
      const currentSettings = settingsStore.settings;
      const settingsChanged = lastSettings !== currentSettings;

      if (this.isVisible && (!wasVisible || settingsChanged)) {
        this.refreshBanners();
      }
      
      // Always update lastSettings to keep it in sync
      lastSettings = currentSettings;
    }, 50); // 50ms for very responsive updates
  },

  // Update visibility based on current context
  updateVisibility() {
    const hasContext = !!getContext();
    this.isVisible = !hasContext;
  },

  // Hide welcome screen
  hide() {
    this.isVisible = false;
  },

  // Show welcome screen
  show() {
    this.isVisible = true;
    this.refreshBanners();
  },

  get sortedBanners() {
    return bannerStore.sortBanners(this.banners);
  },

  getBannerClass(bannerOrType) {
    return bannerStore.getBannerClass(bannerOrType, "welcome-banner");
  },

  getBannerIcon(type) {
    return bannerStore.getBannerIcon(type);
  },

  async loadSettingsSnapshot() {
    try {
      const response = await API.callJsonApi("settings_get", null);
      return response;
    } catch (error) {
      console.error("Failed to load settings for banners:", error);
      return null;
    }
  },

  buildBannerContext(settingsSnapshot) {
    const location = new URL(window.location.href);
    return {
      url: window.location.href,
      hostname: location.hostname,
      protocol: location.protocol.replace(":", ""),
      browser: navigator.userAgent,
      time: new Date().toISOString(),
      selected_provider: settingsSnapshot?.settings?.chat_model_provider || null,
    };
  },

  runFrontendBannerChecks(context, settingsSnapshot) {
    const settings = settingsSnapshot?.settings || {};
    const additional = settingsSnapshot?.additional || {};
    const input = { context, settings, additional };
    return bannerStore.runChecks("welcome", input);
  },

  async runBackendBannerChecks(frontendBanners, context) {
    try {
      const response = await API.callJsonApi("welcome_banners", {
        context,
        frontend_banners: frontendBanners,
      });
      if (Array.isArray(response?.banners)) {
        return response.banners;
      }
      return [];
    } catch (error) {
      console.error("Failed to load backend banners:", error);
      return [];
    }
  },

  async refreshBanners() {
    if (this.bannerChecksInFlight) return;
    this.bannerChecksInFlight = true;
    try {
      const settingsSnapshot = await this.loadSettingsSnapshot();
      const context = this.buildBannerContext(settingsSnapshot);
      const frontendBanners = this.runFrontendBannerChecks(
        context,
        settingsSnapshot
      );

      const backendBanners = await this.runBackendBannerChecks(
        frontendBanners,
        context
      );
      this.banners = bannerStore.mergeBanners(frontendBanners, backendBanners);
    } finally {
      this.bannerChecksInFlight = false;
    }
  },

  openSettingsTab(tab) {
    settingsStore.open(tab || null);
  },

  // Execute an action by ID
  executeAction(actionId) {
    switch (actionId) {
      case "new-chat":
        chatsStore.newChat();
        break;
      case "settings":
        // Open settings modal
        const settingsButton = document.getElementById("settings");
        if (settingsButton) {
          settingsButton.click();
        }
        break;
      case "projects":
        projectsStore.openProjectsModal();
        break;
      case "memory":
        memoryStore.openModal();
        break;
      case "website":
        window.open("https://agent-zero.ai", "_blank");
        break;
      case "github":
        window.open("https://github.com/agent0ai/agent-zero", "_blank");
        break;
    }
  },
};

// Create and export the store
const store = createStore("welcomeStore", model);
export { store };
