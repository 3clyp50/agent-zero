const fileBrowserModalProxy = {
  isOpen: false,
  isLoading: false,

  browser: {
    title: "File Browser",
    currentPath: "",
    entries: [],
    parentPath: "",
    sortBy: "name",
    sortDirection: "asc",
  },

  // Initialize navigation history
  history: [],

  async openModal(path) {
    const modalEl = document.getElementById("fileBrowserModal");
    const modalAD = Alpine.$data(modalEl);

    modalAD.isOpen = true;
    modalAD.isLoading = true;

    // Get updated path from sidebar data if available
    const sidebarData = Alpine.$data(document.getElementById('files-section'));
    const updatedPath = path || (sidebarData && sidebarData.currentPath ? sidebarData.currentPath : fileBrowserModalProxy.browser.currentPath) || "$WORK_DIR";

    // Update the entire browser object to ensure reactivity
    modalAD.browser = {
      ...modalAD.browser,
      currentPath: updatedPath
    };

    await modalAD.fetchFiles(updatedPath);
    
    // Force update the browser object again after fetch
    modalAD.browser = {
      ...modalAD.browser,
      currentPath: updatedPath
    };

  },

  isArchive(filename) {
    const archiveExts = ["zip", "tar", "gz", "rar", "7z"];
    const ext = filename.split(".").pop().toLowerCase();
    return archiveExts.includes(ext);
  },

  async fetchFiles(path = "") {
    this.isLoading = true;
    try {
      const response = await fetch(
        `/get_work_dir_files?path=${encodeURIComponent(path)}`
      );

      if (response.ok) {
        const data = await response.json();
        this.browser.entries = data.data.entries;
        this.browser.currentPath = data.data.current_path;
        this.browser.parentPath = data.data.parent_path;
                
        // Update sidebar files section
        const filesSection = Alpine.$data(document.getElementById('files-section'));
        if (filesSection) {
          filesSection.entries = data.data.entries;
          filesSection.currentPath = data.data.current_path;
          filesSection.parentPath = data.data.parent_path;
        }
      } else {
        console.error("Error fetching files:", await response.text());
        this.browser.entries = [];
      }
    } catch (error) {
      window.toastFetchError("Error fetching files", error);
      this.browser.entries = [];
    } finally {
      this.isLoading = false;
    }
  },

  async navigateToFolder(path) {
    // Push current path to history before navigating
    if (this.browser.currentPath !== path) {
      this.history.push(this.browser.currentPath);
    }
    await this.fetchFiles(path);
    // Refresh all browsers after navigation
    await this.refreshAllBrowsers();
  },

  async navigateUp() {
    if (this.browser.parentPath !== "") {
      // Push current path to history before navigating up
      this.history.push(this.browser.currentPath);
      await this.fetchFiles(this.browser.parentPath);
      // Refresh all browsers after navigation
      await this.refreshAllBrowsers();
    }
  },

  sortFiles(entries) {
    return [...entries].sort((a, b) => {
      // Folders always come first
      if (a.is_dir !== b.is_dir) {
        return a.is_dir ? -1 : 1;
      }

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
      this.browser.sortDirection =
        this.browser.sortDirection === "asc" ? "desc" : "asc";
    } else {
      this.browser.sortBy = column;
      this.browser.sortDirection = "asc";
    }
  },

  async deleteFile(file) {
    if (!confirm(`Are you sure you want to delete ${file.name}?`)) {
      return;
    }

    try {
      const response = await fetch("/delete_work_dir_file", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          path: file.path,
          currentPath: this.browser.currentPath,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        // Instead of just filtering, refresh all browsers
        await this.refreshAllBrowsers();
        alert("File deleted successfully.");
      } else {
        alert(`Error deleting file: ${await response.text()}`);
      }
    } catch (error) {
      window.toastFetchError("Error deleting file", error);
      alert("Error deleting file");
    }
  },

  async handleFileUpload(event) {
    try {
      const files = event.target.files;
      if (!files.length) return;

      const formData = new FormData();
      // Use the shared state's currentPath
      formData.append("path", this.browser.currentPath);

      for (let i = 0; i < files.length; i++) {
        const ext = files[i].name.split(".").pop().toLowerCase();
        if (!["zip", "tar", "gz", "rar", "7z"].includes(ext)) {
          if (files[i].size > 100 * 1024 * 1024) {
            alert(`File ${files[i].name} exceeds the maximum allowed size of 100MB.`);
            continue;
          }
        }
        formData.append("files[]", files[i]);
      }

      const response = await fetch("/upload_work_dir_files", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        // Refresh all browsers after successful upload
        await this.refreshAllBrowsers();

        if (data.failed && data.failed.length > 0) {
          const failedFiles = data.failed
            .map((file) => `${file.name}: ${file.error}`)
            .join("\n");
          alert(`Some files failed to upload:\n${failedFiles}`);
        }
      } else {
        const data = await response.json();
        alert(data.message);
      }
    } catch (error) {
      window.toastFetchError("Error uploading files", error);
      alert("Error uploading files");
    }
  },

  async downloadFile(file) {
    try {
      const downloadUrl = `/download_work_dir_file?path=${encodeURIComponent(
        file.path
      )}`;

      const response = await fetch(downloadUrl);

      if (!response.ok) {
        throw new Error("Network response was not ok");
      }

      const blob = await response.blob();

      const link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = file.name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(link.href);
    } catch (error) {
      window.toastFetchError("Error downloading file", error);
      alert("Error downloading file");
    }
  },

  // Helper Functions
  formatFileSize(size) {
    if (size === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(size) / Math.log(k));
    return parseFloat((size / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  },

  formatDate(dateString) {
    const options = {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    };
    return new Date(dateString).toLocaleDateString(undefined, options);
  },

  handleClose() {
    this.isOpen = false;
  },

  // Add a new method to update all file browser instances
  async refreshAllBrowsers() {
    await this.fetchFiles(this.browser.currentPath);
    
    // Update sidebar files section if it exists
    const filesSection = Alpine.$data(document.getElementById('files-section'));
    if (filesSection) {
      filesSection.entries = this.browser.entries;
      filesSection.currentPath = this.browser.currentPath;
      filesSection.parentPath = this.browser.parentPath;
      filesSection.isLoading = false;

      const sidebarPathText = document.getElementById('files-section').querySelector('#path-text');
      if (sidebarPathText) {
        sidebarPathText.textContent = this.browser.currentPath;
      }
    }

    // Update the modal's current path using Alpine's reactive data if modal is open
    const modalEl = document.getElementById('fileBrowserModal');
    if (modalEl && Alpine.$data(modalEl) && this.isOpen) {
      const modalData = Alpine.$data(modalEl);
      // Create an entirely new browser object to force reactivity
      modalData.browser = {
        title: modalData.browser.title,
        currentPath: this.browser.currentPath,
        entries: this.browser.entries,
        parentPath: this.browser.parentPath,
        sortBy: modalData.browser.sortBy,
        sortDirection: modalData.browser.sortDirection
      };
    }
  },
};

// Wait for Alpine to be ready
document.addEventListener("alpine:init", () => {
  // File browser modal
  Alpine.data("fileBrowserModalProxy", () => ({
    init() {
      Object.assign(this, fileBrowserModalProxy);
      
      this.$watch("isOpen", async (value) => {
        if (value) {
          await this.fetchFiles(this.browser.currentPath);
        }
      });

      // Initial file fetch for sidebar
      this.fetchFiles("$WORK_DIR");
    },
  }));

  // Sidebar file browser
  Alpine.data("files-section", () => ({
    entries: [],
    isLoading: true,
    currentPath: "$WORK_DIR",
    parentPath: "",

    init() {
      // Initial file fetch for sidebar
      fileBrowserModalProxy.fetchFiles("$WORK_DIR").then(() => {
        this.entries = fileBrowserModalProxy.browser.entries;
        this.currentPath = fileBrowserModalProxy.browser.currentPath;
        this.parentPath = fileBrowserModalProxy.browser.parentPath;
        this.isLoading = false;
      });
    },

    async navigateUp() {
      if (this.parentPath !== "") {
        await fileBrowserModalProxy.navigateUp();
        // State will be updated through refreshAllBrowsers
      }
    },

    async navigateToFolder(path) {
      await fileBrowserModalProxy.navigateToFolder(path);
      // State will be updated through refreshAllBrowsers
    },

    async handleFileUpload(event) {
      // Delegate to the proxy's handleFileUpload to ensure consistent context
      await fileBrowserModalProxy.handleFileUpload(event);
    },

    downloadFile(file) {
      fileBrowserModalProxy.downloadFile(file);
    },

    deleteFile(file) {
      fileBrowserModalProxy.deleteFile(file);
    },

    isArchive(filename) {
      return fileBrowserModalProxy.isArchive(filename);
    }
  }));
});

// Keep the global assignment for backward compatibility
window.fileBrowserModalProxy = fileBrowserModalProxy;
fileBrowserModalProxy.handleFileUpload = fileBrowserModalProxy.handleFileUpload.bind(fileBrowserModalProxy);

openFileLink = async function (path) {
  try {
    const resp = await window.sendJsonData("/file_info", { path });
    if (!resp.exists) {
      window.toast("File does not exist.", "error");
      return;
    }

    if (resp.is_dir) {
      fileBrowserModalProxy.openModal(resp.abs_path);
    } else {
      fileBrowserModalProxy.downloadFile({
        path: resp.abs_path,
        name: resp.file_name,
      });
    }
  } catch (e) {
    window.toastFetchError("Error opening file", e);
  }
};
window.openFileLink = openFileLink;
