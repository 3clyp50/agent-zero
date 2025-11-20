import { createStore } from "/js/AlpineStore.js";

const sendJsonData = globalThis.sendJsonData;
const toast = globalThis.toast;

function getContainerStore() {
  return globalThis.Alpine?.store("containerStorage");
}

export const store = createStore("contentSync", {
  targetPath: "",
  includePrompts: true,
  includeKnowledge: true,
  cleanDestination: false,
  busy: false,
  error: "",
  lastResult: null,
  log: [],

  init() {
    if (!this.targetPath) {
      const candidates = this.detectedHostPaths();
      if (candidates.length > 0) {
        this.targetPath = candidates[0];
      }
    }
  },

  detectedHostPaths() {
    const containerStore = getContainerStore();
    if (!containerStore?.snapshot?.containers) {
      return [];
    }
    const paths = new Set();
    for (const container of containerStore.snapshot.containers) {
      for (const mount of container.mounts || []) {
        if (mount.type === "bind" && mount.source) {
          paths.add(mount.source);
        }
      }
    }
    if (containerStore?.snapshot?.volumes) {
      for (const volume of containerStore.snapshot.volumes) {
        if (volume.mountpoint) {
          paths.add(volume.mountpoint);
        }
      }
    }
    return Array.from(paths);
  },

  toggleAll(include) {
    this.includePrompts = include;
    this.includeKnowledge = include;
  },

  async sync(direction) {
    if (this.busy) return;
    this.error = "";
    this.lastResult = null;

    const trimmedPath = (this.targetPath || "").trim();
    if (!trimmedPath) {
      this.error = "Enter a destination folder that is mounted into the container.";
      if (toast) toast(this.error, "error");
      return;
    }

    const items = [];
    if (this.includePrompts) items.push("prompts");
    if (this.includeKnowledge) items.push("knowledge");
    if (items.length === 0) {
      this.error = "Select at least one content type to sync.";
      if (toast) toast(this.error, "error");
      return;
    }

    this.busy = true;
    try {
      const response = await sendJsonData("/persistent_sync", {
        direction,
        target_path: trimmedPath,
        items,
        clean_destination: this.cleanDestination,
      });
      if (!response?.success) {
        const message = response?.error || "Sync failed";
        this.error = message;
        if (toast) toast(message, "error");
        return;
      }
      this.lastResult = response;
      this.log = response.log || [];
      if (toast) {
        const verb = direction === "backup" ? "Backed up" : "Restored";
        toast(`${verb} prompts/knowledge successfully.`, "success");
      }
    } catch (error) {
      const message = error?.message || "Sync failed";
      this.error = message;
      if (toast) toast(message, "error");
    } finally {
      this.busy = false;
    }
  }
});
