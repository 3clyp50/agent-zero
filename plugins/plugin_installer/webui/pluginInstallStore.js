import { createStore, getStore } from "/js/AlpineStore.js";
import * as api from "/js/api.js";
import { openModal } from "/js/modals.js";
import { marked } from "/vendor/marked/marked.esm.js";
import { toastFrontendSuccess } from "/components/notifications/notification-store.js";
import { showConfirmDialog } from "/js/confirmDialog.js";
import "/components/plugins/list/pluginListStore.js";
import "/components/plugins/list/plugin-init-store.js";
import "/components/modals/image-viewer/image-viewer-store.js";

const PLUGIN_API = "plugins/plugin_installer/plugin_install";
const PER_PAGE = 20;

const SECURITY_WARNING = {
  title: "Security Warning",
  message: `
    <p><strong>Installing plugins from untrusted sources may pose security risks:</strong></p>
    <ul style="margin: 0.75em 0; padding-left: 1.5em;">
      <li>Malicious code execution</li>
      <li>Exposure of sensitive data</li>
      <li>System compromise</li>
    </ul>
    <p style="margin-top: 0.75em;">Only install plugins from sources you trust.</p>
  `,
  type: "warning",
  confirmText: "Install Anyway",
  cancelText: "Cancel",
};

const model = {
  // ZIP install state
  zipFile: null,
  zipFileName: "",

  // Git install state
  gitUrl: "",
  gitToken: "",

  // Index state
  index: null,
  installedPlugins: [],
  search: "",
  page: 1,
  sortBy: "stars",
  browseFilter: "all",
  selectedPlugin: null,

  // Shared state
  loading: false,
  loadingMessage: "",
  error: "",

  // README state
  readmeContent: null,
  readmeLoading: false,

  // Installed plugin detail (for manage buttons)
  installedPluginInfo: null,

  // Detail hero thumbnail fallbacks
  detailPluginName: "",
  /** @type {string[]} */
  detailThumbnailSources: [],
  detailThumbnailIndex: 0,

  // Tab state
  activeTab: "store",

  setTab(tab) {
    this.activeTab = tab;
    this.error = "";
  },

  setBrowseFilter(filter) {
    this.browseFilter = filter || "all";
    this.page = 1;
  },

  /** Normalize GitHub URL and return raw.githubusercontent.com base (no trailing slash). */
  _githubRawBase(githubUrl) {
    if (!githubUrl || typeof githubUrl !== "string") return null;
    let url = githubUrl.trim().replace(/\.git$/i, "");
    if (!url.includes("github.com")) return null;
    return url.replace("https://github.com/", "https://raw.githubusercontent.com/");
  },

  _pluginName(plugin) {
    const repoUrl = (plugin?.github || "").replace(/\.git$/, "");
    return repoUrl.split("/").pop() || plugin?.key || "";
  },

  _pluginPrimaryTag(plugin) {
    const tags = Array.isArray(plugin?.tags) ? plugin.tags.filter(Boolean) : [];
    return tags[0] || "";
  },

  _formatBrowseTag(tag) {
    if (!tag || typeof tag !== "string") return "";
    return tag
      .split(/[-_]/)
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  },

  _matchesBrowseFilter(plugin, filterKey) {
    if (!filterKey || filterKey === "all") return true;
    if (filterKey === "installed") return !!plugin?.installed;
    if (filterKey === "popular") return (plugin?.stars || 0) > 0;
    if (filterKey.startsWith("tag:")) {
      return this._pluginPrimaryTag(plugin) === filterKey.slice(4);
    }
    return false;
  },

  // ── ZIP Install ──────────────────────────────

  handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    this.zipFile = file;
    this.zipFileName = file.name;
    this.error = "";
  },

  async installZip() {
    if (!this.zipFile) {
      this.error = "Please select a ZIP file first";
      return;
    }

    const confirmed = await showConfirmDialog(SECURITY_WARNING);
    if (!confirmed) return;

    try {
      this.loading = true;
      this.loadingMessage = "Installing plugin from ZIP...";
      this.error = "";

      const formData = new FormData();
      formData.append("action", "install_zip");
      formData.append("plugin_file", this.zipFile);

      const response = await api.fetchApi(PLUGIN_API, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (!data.success) {
        this.error = data.error || "Installation failed";
        return;
      }

      toastFrontendSuccess(
        `Plugin "${data.title || data.plugin_name}" installed`,
        "Plugin Installer"
      );
    } catch (e) {
      this.error = `Installation error: ${e.message}`;
    } finally {
      this.loading = false;
      this.loadingMessage = "";
    }
  },

  // ── Git Install ──────────────────────────────

  async installGit() {
    const url = (this.gitUrl || "").trim();
    if (!url) {
      this.error = "Please enter a Git URL";
      return;
    }

    const confirmed = await showConfirmDialog(SECURITY_WARNING);
    if (!confirmed) return;

    try {
      this.loading = true;
      this.loadingMessage = "Cloning repository...";
      this.error = "";

      const data = await api.callJsonApi(PLUGIN_API, {
        action: "install_git",
        git_url: url,
        git_token: this.gitToken || "",
      });

      if (!data.success) {
        this.error = data.error || "Clone failed";
        return;
      }

      toastFrontendSuccess(
        `Plugin "${data.title || data.plugin_name}" installed`,
        "Plugin Installer"
      );
    } catch (e) {
      this.error = `Clone error: ${e.message}`;
    } finally {
      this.loading = false;
      this.loadingMessage = "";
    }
  },

  // ── Index Browse ─────────────────────────────

  async fetchIndex() {
    try {
      this.loading = true;
      this.loadingMessage = "Loading plugin index...";
      this.error = "";
      this.index = null;

      const data = await api.callJsonApi(PLUGIN_API, {
        action: "fetch_index",
      });

      if (!data.success) {
        this.error = data.error || "Failed to load index";
        return;
      }

      this.index = data.index;
      this.installedPlugins = data.installed_plugins || [];
      this.page = 1;
    } catch (e) {
      this.error = `Failed to load plugin index: ${e.message}`;
    } finally {
      this.loading = false;
      this.loadingMessage = "";
    }
  },

  get pluginsList() {
    if (!this.index?.plugins) return [];
    return Object.entries(this.index.plugins).map(([key, val]) => ({
      key,
      ...val,
      installed: this.installedPlugins.includes(key),
    }));
  },

  get browseFilters() {
    const plugins = this.pluginsList;
    const filters = [{ key: "all", label: "All", count: plugins.length }];

    if (!plugins.length) return filters;

    const installedCount = plugins.filter((plugin) => plugin.installed).length;
    if (installedCount) {
      filters.push({ key: "installed", label: "Installed", count: installedCount });
    }

    const popularCount = plugins.filter((plugin) => (plugin.stars || 0) > 0).length;
    if (popularCount) {
      filters.push({ key: "popular", label: "Popular", count: popularCount });
    }

    const tagCounts = new Map();
    for (const plugin of plugins) {
      const tag = this._pluginPrimaryTag(plugin);
      if (!tag) continue;
      tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
    }

    for (const [tag, count] of Array.from(tagCounts.entries())
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, 4)) {
      filters.push({
        key: `tag:${tag}`,
        label: this._formatBrowseTag(tag),
        count,
      });
    }

    return filters;
  },

  get filteredPlugins() {
    let list = this.pluginsList.filter((plugin) =>
      this._matchesBrowseFilter(plugin, this.browseFilter)
    );
    const q = (this.search || "").toLowerCase().trim();
    if (q) {
      list = list.filter(
        (p) =>
          (p.title || "").toLowerCase().includes(q) ||
          (p.author || "").toLowerCase().includes(q) ||
          (p.description || "").toLowerCase().includes(q) ||
          (p.key || "").toLowerCase().includes(q) ||
          (p.tags || []).some((t) => t.toLowerCase().includes(q))
      );
    }
    if (this.sortBy === "stars") {
      list.sort((a, b) => (b.stars || 0) - (a.stars || 0));
    } else {
      list.sort((a, b) =>
        (a.title || a.key).localeCompare(b.title || b.key)
      );
    }
    return list;
  },

  get browseResultsSummary() {
    const total = this.pluginsList.length;
    const visible = this.filteredPlugins.length;
    if (!total) return "No plugins available";
    if (visible === total) {
      return `${total} plugin${total === 1 ? "" : "s"} available`;
    }
    return `Showing ${visible} of ${total} plugins`;
  },

  get totalPages() {
    return Math.max(1, Math.ceil(this.filteredPlugins.length / PER_PAGE));
  },

  get paginatedPlugins() {
    const start = (this.page - 1) * PER_PAGE;
    return this.filteredPlugins.slice(start, start + PER_PAGE);
  },

  getBrowseSubtitle(plugin) {
    const author = (plugin?.author || "").trim();
    if (author) return author;
    const tag = this._pluginPrimaryTag(plugin);
    if (tag) return this._formatBrowseTag(tag);
    return plugin?.key || "";
  },

  getBrowsePrimaryTag(plugin) {
    return this._formatBrowseTag(this._pluginPrimaryTag(plugin));
  },

  setPage(p) {
    this.page = Math.max(1, Math.min(p, this.totalPages));
  },

  openDetail(plugin) {
    this.selectedPlugin = plugin;
    this.error = "";
    this.installedPluginInfo = null;
    this.readmeContent = null;
    this.detailPluginName = this._pluginName(plugin);
    this.detailThumbnailSources = this.getDetailThumbnailSources(plugin);
    this.detailThumbnailIndex = 0;
    if (plugin.installed) {
      this.fetchInstalledPluginInfo(this.detailPluginName);
    }
    this.fetchReadme(plugin);
    openModal("/plugins/plugin_installer/webui/install-detail.html");
  },

  async fetchReadme(plugin) {
    const rawBase = this._githubRawBase(plugin?.github);
    if (!rawBase) return;

    try {
      this.readmeLoading = true;
      this.readmeContent = null;

      const response = await fetch(`${rawBase}/main/README.md`);
      if (response.ok) {
        const readme = await response.text();
        this.readmeContent = marked.parse(readme, { breaks: true });
      }
    } catch (e) {
      console.warn("Failed to fetch readme:", e);
    } finally {
      this.readmeLoading = false;
    }
  },

  async installFromIndex(plugin) {
    if (!plugin?.github) {
      this.error = "No GitHub URL available for this plugin";
      return;
    }

    const confirmed = await showConfirmDialog(SECURITY_WARNING);
    if (!confirmed) return;

    try {
      this.loading = true;
      this.loadingMessage = `Installing ${plugin.title || plugin.key}...`;
      this.error = "";

      const data = await api.callJsonApi(PLUGIN_API, {
        action: "install_git",
        git_url: plugin.github,
      });

      if (!data.success) {
        this.error = data.error || "Installation failed";
        return;
      }

      if (!this.installedPlugins.includes(plugin.key)) {
        this.installedPlugins.push(plugin.key);
      }
      plugin.installed = true;
      this.selectedPlugin = { ...this.selectedPlugin, installed: true };
      this.detailPluginName = data.plugin_name;
      this.detailThumbnailSources = this.getDetailThumbnailSources(this.selectedPlugin);
      this.detailThumbnailIndex = 0;
      this.fetchInstalledPluginInfo(data.plugin_name);

      toastFrontendSuccess(
        `Plugin "${data.title || data.plugin_name}" installed`,
        "Plugin Installer"
      );
    } catch (e) {
      this.error = `Installation error: ${e.message}`;
    } finally {
      this.loading = false;
      this.loadingMessage = "";
    }
  },

  // ── Installed Plugin Info ─────────────────────

  async fetchInstalledPluginInfo(pluginName) {
    this.installedPluginInfo = null;
    try {
      const response = await api.callJsonApi("plugins_list", {
        filter: { custom: true, builtin: true, search: "" },
      });
      const plugins = Array.isArray(response.plugins) ? response.plugins : [];
      this.installedPluginInfo = plugins.find((p) => p.name === pluginName) || null;
    } catch (e) {
      this.installedPluginInfo = null;
    }
  },

  _pluginListStore() {
    return getStore("pluginListStore");
  },

  _pluginInitStore() {
    return getStore("pluginInitStore");
  },

  manageOpenPlugin() {
    const info = this.installedPluginInfo;
    if (!info?.name || !info?.has_main_screen) return;
    openModal(`/plugins/${info.name}/webui/main.html`);
  },

  async manageOpenConfig() {
    const pls = this._pluginListStore();
    if (pls?.openPluginConfig && this.installedPluginInfo) {
      await pls.openPluginConfig(this.installedPluginInfo);
    }
  },

  async manageOpenDoc(doc) {
    const pls = this._pluginListStore();
    if (pls?.openPluginDoc && this.installedPluginInfo) {
      await pls.openPluginDoc(this.installedPluginInfo, doc);
    }
  },

  manageOpenInfo() {
    const pls = this._pluginListStore();
    if (pls?.openPluginInfo && this.installedPluginInfo) {
      pls.openPluginInfo(this.installedPluginInfo);
    }
  },

  manageOpenInit() {
    const initStore = this._pluginInitStore();
    if (initStore?.open && this.installedPluginInfo) {
      initStore.open(this.installedPluginInfo);
    }
  },

  async manageDeletePlugin() {
    const pls = this._pluginListStore();
    if (pls?.deletePlugin && this.installedPluginInfo) {
      await pls.deletePlugin(this.installedPluginInfo);
      if (this.selectedPlugin) {
        this.selectedPlugin.installed = false;
        const idx = this.installedPlugins.indexOf(this.selectedPlugin.key);
        if (idx !== -1) this.installedPlugins.splice(idx, 1);
      }
      this.installedPluginInfo = null;
    }
  },

  getIndexUrl(pluginKey) {
    if (!pluginKey) return "";
    return `https://github.com/agent0ai/a0-plugins/tree/main/plugins/${pluginKey}`;
  },

  getThumbnailUrl(plugin) {
    if (!plugin) return null;
    if (plugin.thumbnail && typeof plugin.thumbnail === "string") return plugin.thumbnail;
    const rawBase = this._githubRawBase(plugin?.github);
    return rawBase ? `${rawBase}/main/thumbnail.png` : null;
  },

  getLocalThumbnailUrl() {
    const name = this.detailPluginName;
    return name ? `/plugins/${name}/thumbnail.png` : null;
  },

  /**
   * Build the ordered thumbnail URLs for the detail view.
   * First try GitHub, then the local plugin asset.
   * @param {any} plugin
   * @returns {string[]}
   */
  getDetailThumbnailSources(plugin) {
    const currentPlugin = plugin || this.selectedPlugin;
    const sources = [
      this.getThumbnailUrl(currentPlugin),
      this.getLocalThumbnailUrl(),
    ];
    return sources.filter(
      (url, index) => typeof url === "string" && sources.indexOf(url) === index
    );
  },

  getDetailThumbnailUrl() {
    return this.detailThumbnailSources[this.detailThumbnailIndex] || null;
  },

  nextDetailThumbnail() {
    this.detailThumbnailIndex += 1;
  },

  // ── Shared ───────────────────────────────────

  resetZip() {
    this.zipFile = null;
    this.zipFileName = "";
    this.error = "";
  },

  resetGit() {
    this.gitUrl = "";
    this.gitToken = "";
    this.error = "";
  },

  resetIndex() {
    this.search = "";
    this.page = 1;
    this.sortBy = "stars";
    this.browseFilter = "all";
    this.error = "";
    this.selectedPlugin = null;
  },

  /** Called from x-destroy when the installer modal is torn down; refreshes the plugin list store */
  refreshPluginList() {
    getStore("pluginListStore")?.refresh();
  },

  truncate(text, max) {
    if (!text || text.length <= max) return text || "";
    return text.substring(0, max) + "...";
  },
};

const store = createStore("pluginInstallStore", model);
export { store };
