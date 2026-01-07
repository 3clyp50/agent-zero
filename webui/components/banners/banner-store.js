import { createStore } from "/js/AlpineStore.js";

export const BANNER_TYPES = Object.freeze({
  INFO: "info",
  WARNING: "warning",
  ERROR: "error",
});

export const BANNER_PRIORITY = Object.freeze({
  HIGH: 100,
  MEDIUM: 50,
  LOW: 10,
});

const model = {
  checksByScope: {},

  registerCheck(scope, check) {
    if (!scope || typeof check !== "function") return;
    const registry = this.checksByScope[scope] || [];
    registry.push(check);
    this.checksByScope[scope] = registry;
  },

  runChecks(scope, input) {
    const checks = this.checksByScope[scope] || [];
    return checks.flatMap((check) => check(input) || []);
  },

  createBanner({ id, title, type, priority, html }) {
    return {
      id: id || null,
      title: title?.trim() || "",
      type: type || BANNER_TYPES.INFO,
      priority: Number.isFinite(priority) ? priority : 0,
      html: html || "",
    };
  },

  normalizeBanner(banner, source) {
    if (!banner || typeof banner !== "object") return null;
    const normalized = this.createBanner(banner);
    if (!normalized.title || !normalized.html) return null;
    return { ...normalized, source };
  },

  assignBannerKeys(banners) {
    return banners.map((banner, index) => ({
      ...banner,
      key: banner.id || `${banner.source || "banner"}-${index}`,
    }));
  },

  mergeBanners(frontendBanners, backendBanners) {
    const merged = [];
    const seenIds = new Set();
    const addBanner = (banner, source) => {
      const normalized = this.normalizeBanner(banner, source);
      if (!normalized) return;
      if (normalized.id) {
        if (seenIds.has(normalized.id)) return;
        seenIds.add(normalized.id);
      }
      merged.push(normalized);
    };

    (frontendBanners || []).forEach((banner) => addBanner(banner, "frontend"));
    (backendBanners || []).forEach((banner) => addBanner(banner, "backend"));
    return this.assignBannerKeys(merged);
  },

  sortBanners(banners) {
    return [...(banners || [])].sort((a, b) => {
      const priorityA = Number.isFinite(a?.priority) ? a.priority : 0;
      const priorityB = Number.isFinite(b?.priority) ? b.priority : 0;
      return priorityB - priorityA;
    });
  },

  getBannerClass(type, prefix = "banner") {
    const normalized = type || BANNER_TYPES.INFO;
    return `${prefix}-${normalized}`;
  },

  getBannerIcon(type) {
    switch (type) {
      case BANNER_TYPES.WARNING:
        return "warning";
      case BANNER_TYPES.ERROR:
        return "error";
      default:
        return "info";
    }
  },
};

const store = createStore("bannerStore", model);

export { store };
