import { createStore } from "/js/AlpineStore.js";

const model = {
  // UI state
  isOpen: false,
  isLoading: false,

  // Browser state
  browser: {
    title: "File Browser",
    currentPath: "",
    entries: [],
    parentPath: "",
    sortBy: "name",
    sortDirection: "asc",
  },

  // Simple navigation history (local to this session)
  history: [],

  // Lifecycle hook for side-effects
  init() {
    // No-op for now; kept for parity and future wiring
  },

  // Helpers
  isArchive(filename) {
    const archiveExts = ["zip", "tar", "gz", "rar", "7z"];
    const ext = String(filename || "").split(".").pop().toLowerCase();
    return archiveExts.includes(ext);
  },

  async openModal(path) {
    this.isOpen = true;
    this.isLoading = true;

    if (path) this.browser.currentPath = path;
    else if (!this.browser.currentPath) this.browser.currentPath = "$WORK_DIR";

    await this.fetchFiles(this.browser.currentPath);
  },

  async fetchFiles(path = "") {
    this.isLoading = true;
    try {
      const response = await fetchApi(`/get_work_dir_files?path=${encodeURIComponent(path)}`);
      if (response.ok) {
        const data = await response.json();
        this.browser.entries = data.data.entries;
        this.browser.currentPath = data.data.current_path;
        this.browser.parentPath = data.data.parent_path;
      } else {
        console.error("Error fetching files:", await response.text());
        this.browser.entries = [];
      }
    } catch (error) {
      window.toastFrontendError("Error fetching files: " + error.message, "File Browser Error");
      this.browser.entries = [];
    } finally {
      this.isLoading = false;
    }
  },

  async navigateToFolder(path) {
    if (this.browser.currentPath !== path) this.history.push(this.browser.currentPath);
    await this.fetchFiles(path);
  },

  async navigateUp() {
    if (this.browser.parentPath !== "") {
      this.history.push(this.browser.currentPath);
      await this.fetchFiles(this.browser.parentPath);
    }
  },

  sortFiles(entries) {
    return [...entries].sort((a, b) => {
      // Folders first
      if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1;

      const direction = this.browser.sortDirection === "asc" ? 1 : -1;
      switch (this.browser.sortBy) {
        case "name":
          return direction * a.name.localeCompare(b.name);
        case "size":
          return direction * (a.size - b.size);
        case "date":
          return direction * (new Date(a.modified) - new Date(b.modified));
        default:
          return 0;
      }
    });
  },

  toggleSort(column) {
    if (this.browser.sortBy === column) {
      this.browser.sortDirection = this.browser.sortDirection === "asc" ? "desc" : "asc";
    } else {
      this.browser.sortBy = column;
      this.browser.sortDirection = "asc";
    }
  },

  async deleteFile(file) {
    if (!confirm(`Are you sure you want to delete ${file.name}?`)) return;

    try {
      const response = await fetchApi("/delete_work_dir_file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: file.path, currentPath: this.browser.currentPath }),
      });

      if (response.ok) {
        this.browser.entries = this.browser.entries.filter((entry) => entry.path !== file.path);
        alert("File deleted successfully.");
      } else {
        const txt = await response.text();
        alert(`Error deleting file: ${txt}`);
      }
    } catch (error) {
      window.toastFrontendError("Error deleting file: " + error.message, "File Delete Error");
      alert("Error deleting file");
    }
  },

  async handleFileUpload(event) {
    try {
      const files = event.target.files || [];
      if (!files.length) return;

      const formData = new FormData();
      formData.append("path", this.browser.currentPath);

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const ext = String(file.name || "").split(".").pop().toLowerCase();
        if (!["zip", "tar", "gz", "rar", "7z"].includes(ext)) {
          if (file.size > 100 * 1024 * 1024) { // 100MB
            alert(`File ${file.name} exceeds the maximum allowed size of 100MB.`);
            continue;
          }
        }
        formData.append("files[]", file);
      }

      const response = await fetchApi("/upload_work_dir_files", { method: "POST", body: formData });

      if (response.ok) {
        const data = await response.json();
        const failedNames = new Set(
          Array.isArray(data.failed)
            ? data.failed.map((f) => (typeof f === "string" ? f : f?.name)).filter(Boolean)
            : []
        );
        this.browser.entries = data.data.entries.map((entry) => ({
          ...entry,
          uploadStatus: failedNames.has(entry.name) ? "failed" : "success",
        }));
        this.browser.currentPath = data.data.current_path;
        this.browser.parentPath = data.data.parent_path;

        if (data.failed && data.failed.length > 0) {
          const failedFiles = data.failed.map((f) => `${f.name}: ${f.error}`).join("\n");
          alert(`Some files failed to upload:\n${failedFiles}`);
        }
      } else {
        const txt = await response.text();
        alert(txt || "Upload failed");
      }
    } catch (error) {
      window.toastFrontendError("Error uploading files: " + error.message, "File Upload Error");
      alert("Error uploading files");
    }
  },

  downloadFile(file) {
    const link = document.createElement("a");
    link.href = `/download_work_dir_file?path=${encodeURIComponent(file.path)}`;
    link.download = file.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },

  formatFileSize(size) {
    if (size === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(size) / Math.log(k));
    return parseFloat((size / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  },

  formatDate(dateString) {
    const options = { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" };
    return new Date(dateString).toLocaleDateString(undefined, options);
  },

  handleClose() {
    this.isOpen = false;
  },
};

export const store = createStore("fileBrowser", model);

// Backward compatibility: expose legacy globals
globalThis.fileBrowserModalProxy = store;

globalThis.openFileLink = async function (path) {
  try {
    const resp = await window.sendJsonData("/file_info", { path });
    if (!resp.exists) {
      window.toastFrontendError("File does not exist.", "File Error");
      return;
    }

    if (resp.is_dir) {
      store.openModal(resp.abs_path);
    } else {
      store.downloadFile({ path: resp.abs_path, name: resp.file_name });
    }
  } catch (e) {
    window.toastFrontendError("Error opening file: " + e.message, "File Open Error");
  }
};


