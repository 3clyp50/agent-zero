import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";

const MISSING_API_KEY_BANNER_ID = "missing-api-key";

function buildBannersContext() {
  return {
    url: window.location.href,
    protocol: window.location.protocol,
    hostname: window.location.hostname,
    port: window.location.port,
    browser: navigator.userAgent,
    timestamp: new Date().toISOString(),
  };
}

export const store = createStore("composerBanner", {
  missingApiKeys: [],
  loading: false,
  lastRefresh: 0,
  _modalCloseBound: false,

  get hasMissingApiKeys() {
    return (
      Array.isArray(this.missingApiKeys) && this.missingApiKeys.length > 0
    );
  },

  get missingApiKeysSummaryText() {
    if (!this.hasMissingApiKeys) return "";
    return this.missingApiKeys
      .map((p) => `${p.model_type} (${p.provider})`)
      .join(", ");
  },

  init() {
    if (this._modalCloseBound) return;
    this._modalCloseBound = true;
    document.addEventListener("modal-closed", () => {
      this.refresh(true);
    });
  },

  async refresh(force = false) {
    const now = Date.now();
    if (!force && now - this.lastRefresh < 1000) return;
    this.lastRefresh = now;
    this.loading = true;
    try {
      const response = await callJsonApi("/banners", {
        banners: [],
        context: buildBannersContext(),
      });
      const list = response?.banners || [];
      const row = list.find((b) => b?.id === MISSING_API_KEY_BANNER_ID);
      this.missingApiKeys = Array.isArray(row?.missing_providers)
        ? row.missing_providers
        : [];
    } catch (e) {
      console.error("composerBanner refresh failed", e);
      this.missingApiKeys = [];
    } finally {
      this.loading = false;
    }
  },
});
