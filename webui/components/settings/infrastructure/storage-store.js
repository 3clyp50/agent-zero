import { createStore } from "/js/AlpineStore.js";
import { fetchApi } from "/js/api.js";

const toast = globalThis.toast;

export const store = createStore("containerStorage", {
  loading: false,
  error: "",
  snapshot: null,
  lastUpdated: null,

  async refresh() {
    this.loading = true;
    this.error = "";
    try {
      const response = await fetchApi("/docker_volume_overview", { method: "GET" });
      if (!response || !response.ok) {
        const message = response ? await response.text() : "No response";
        throw new Error(message || "Failed to fetch docker volume overview");
      }
      const data = await response.json();
      if (!data.success) {
        const message = data.error || "Docker volume inspection failed";
        this.snapshot = data;
        this.error = message;
        if (toast) toast(message, "error");
        return;
      }
      this.snapshot = data;
      this.lastUpdated = new Date().toISOString();
    } catch (error) {
      const message = error?.message || "Unexpected error while talking to Docker";
      this.error = message;
      if (toast) toast(message, "error");
    } finally {
      this.loading = false;
    }
  }
});
