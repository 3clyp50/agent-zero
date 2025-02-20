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
    console.log('🔵 openModal called with path:', path);
    const modalEl = document.getElementById("fileBrowserModal");
    console.log('🔵 Modal element found:', !!modalEl);
    const modalAD = Alpine.$data(modalEl);
    console.log('🔵 Modal Alpine data:', modalAD ? 'exists' : 'null');

    modalAD.isOpen = true;
    modalAD.isLoading = true;
    console.log('🔵 Modal state set - isOpen:', modalAD.isOpen, 'isLoading:', modalAD.isLoading);

    // Get updated path from sidebar data if available
    const sidebarData = Alpine.$data(document.getElementById('files-section'));
    const updatedPath = path || (sidebarData && sidebarData.currentPath ? sidebarData.currentPath : fileBrowserModalProxy.browser.currentPath) || "$WORK_DIR";
    console.log('🔵 Updated path determined:', updatedPath);

    // Update the entire browser object to ensure reactivity
    modalAD.browser = {
      ...modalAD.browser,
      currentPath: updatedPath
    };

    await modalAD.fetchFiles(updatedPath);
    console.log('🔵 Files fetched for path:', updatedPath);
    
    modalAD.isLoading = false;
    console.log('🔵 Modal loading completed');

    // Setup drag and drop handlers after a longer delay to ensure DOM is fully rendered
    console.log('🔵 Scheduling drag and drop setup');
    setTimeout(() => {
      // Double check modal is still open before setting up
      if (modalAD.isOpen) {
        console.log('🔵 Setting up drag and drop after delay');
        this.setupDragAndDrop();
      } else {
        console.log('🔵 Modal closed before drag and drop setup');
      }
    }, 300); // Increased delay to ensure DOM is ready
  },

  // Add new method to sync sidebar with modal's current path
  async syncSidebarToModal() {
    const filesSection = Alpine.$data(document.getElementById('files-section'));
    if (filesSection) {
      await filesSection.navigateToFolder(this.browser.currentPath);
      // Update the path text manually to ensure it's visible
      const pathText = document.getElementById('files-section').querySelector('#path-text');
      if (pathText) {
        pathText.textContent = this.browser.currentPath;
      }
    }
  },

  // Add new method to sync modal with sidebar's current path
  async syncModalToSidebar() {
    const filesSection = Alpine.$data(document.getElementById('files-section'));
    if (filesSection) {
      await this.navigateToFolder(filesSection.currentPath);
    }
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
  },

  async navigateUp() {
    if (this.browser.parentPath !== "") {
      // Push current path to history before navigating up
      this.history.push(this.browser.currentPath);
      await this.fetchFiles(this.browser.parentPath);
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
        await this.refreshBrowsers();
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

      // Use the new determineUploadPath function
      const uploadPath = this.determineUploadPath(event);
      
      if (!uploadPath) {
        console.error('Could not determine upload path');
        alert('Error: Could not determine upload path');
        return;
      }

      console.debug('Uploading files to path:', uploadPath);

      const formData = new FormData();
      formData.append("path", uploadPath);

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
        // Get the upload source from the file input's data attribute
        const uploadSource = event.target.getAttribute('data-upload-source');
        if (uploadSource === 'modal') {
          // If the upload is from the modal, refresh the modal's file list
          const modalEl = document.getElementById('fileBrowserModal');
          if (modalEl && Alpine.$data(modalEl)) {
            const modalData = Alpine.$data(modalEl);
            await modalData.fetchFiles(modalData.browser.currentPath);
          }
        } else {
          // Otherwise, refresh browsers (sidebar refreshes as well as modal if applicable)
          await this.refreshBrowsers();
        }

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

  // Add new function to determine upload path
  determineUploadPath(event) {
    try {
      // Get explicit upload source from data attribute if set
      const uploadSource = event.target.getAttribute('data-upload-source');
      
      // Get modal and sidebar states
      const modalEl = document.getElementById('fileBrowserModal');
      const modalData = modalEl && Alpine.$data(modalEl);
      
      const sidebarEl = document.getElementById('files-section');
      const sidebarData = sidebarEl && Alpine.$data(sidebarEl);
      
      let uploadPath;

      if (uploadSource === 'modal') {
        uploadPath = modalData?.browser.currentPath;
        console.debug('determineUploadPath: Using modal path from data attribute:', uploadPath);
      } else if (uploadSource === 'sidebar') {
        uploadPath = sidebarData?.currentPath;
        console.debug('determineUploadPath: Using sidebar path from data attribute:', uploadPath);
      } else {
        // Fallback to original detection via DOM ancestry
        const isModalUpload = event.target.closest('#fileBrowserModal') !== null;
        if (isModalUpload && modalData?.isOpen) {
          uploadPath = modalData.browser.currentPath;
          console.debug('determineUploadPath: Using modal path from fallback:', uploadPath);
        } else {
          uploadPath = sidebarData?.currentPath;
          console.debug('determineUploadPath: Using sidebar path from fallback:', uploadPath);
        }
      }
      
      // Fallback to default path if necessary
      if (!uploadPath) {
        uploadPath = this.browser?.currentPath || '$WORK_DIR';
        console.debug('determineUploadPath: Using fallback default path:', uploadPath);
      }
      
      // Validate the path
      if (typeof uploadPath !== 'string' || uploadPath.trim() === '') {
        console.error('determineUploadPath: Invalid upload path:', uploadPath);
        throw new Error('Invalid upload path');
      }
      
      return uploadPath;
    } catch (error) {
      console.error('determineUploadPath: Error determining upload path:', error);
      return null;
    }
  },

  async downloadFile(file) {
    try {
      const downloadUrl = `/download_work_dir_file?path=${encodeURIComponent(file.path)}`;
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
    // Cleanup drag and drop handlers when modal closes
    this.cleanupDragAndDrop();
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

  setupDragAndDrop() {
    console.log('🟣 setupDragAndDrop called');
    
    // First clean up any existing instances
    console.log('🟣 Cleaning up existing drag drop instances');
    this.cleanupDragAndDrop();
    
    // Get modal container and overlay - search in body since content is teleported
    const modalOverlay = Array.from(document.querySelectorAll('body > .modal-overlay'))
      .find(overlay => overlay.querySelector('.modal-title')?.textContent === this.browser.title);
    
    console.log('🟣 Modal overlay found:', !!modalOverlay);
    
    if (!modalOverlay) {
        console.error('🟣 Error: Could not find file browser modal overlay');
        return;
    }
    
    const modalContainer = modalOverlay.querySelector('.modal-container');
    const modalContent = modalOverlay.querySelector('.modal-content');
    const dragdropOverlay = modalContent?.querySelector('.files-dragdrop-overlay');
    
    console.log('🟣 Modal elements found:', {
        modalContainer: !!modalContainer,
        modalContent: !!modalContent,
        dragdropOverlay: !!dragdropOverlay,
        modalContainerClasses: modalContainer?.className,
        modalContentClasses: modalContent?.className,
        dragdropOverlayClasses: dragdropOverlay?.className,
        modalTitle: modalOverlay.querySelector('.modal-title')?.textContent
    });
    
    if (!modalContainer || !modalContent || !dragdropOverlay) {
        console.error('🟣 Error: Could not find required modal elements', {
            modalContainer: modalContainer?.outerHTML?.slice(0, 100) + '...',
            modalContent: modalContent?.outerHTML?.slice(0, 100) + '...',
            dragdropOverlay: dragdropOverlay?.outerHTML?.slice(0, 100) + '...',
            modalTitle: modalOverlay.querySelector('.modal-title')?.textContent
        });
        return;
    }
    
    console.log('🟣 Creating modal drag drop instance');
    const overlayData = Alpine.$data(dragdropOverlay);
    console.log('🟣 Overlay Alpine data:', overlayData ? 'exists' : 'null', overlayData);
    
    this._modalDragDropInstance = DragDropManager.create({
        container: modalContainer,
        overlay: dragdropOverlay,
        onDrop: async (files) => {
            console.log('🟣 Drop event triggered with files:', files.length);
            await this.handleFileUpload(DragDropManager.createUploadEvent(files, 'modal'));
        },
        useCapture: true,
        globalOverlay: document.getElementById('dragdrop-overlay'),
        onDragStart: () => {
            console.log('🟣 Drag start event triggered');
            const overlayData = Alpine.$data(dragdropOverlay);
            console.log('🟣 Overlay data on drag start:', overlayData ? 'exists' : 'null');
            if (overlayData) {
                overlayData.isVisible = true;
                console.log('🟣 Overlay visibility set to true');
            }
        },
        onDragEnd: () => {
            console.log('🟣 Drag end event triggered');
            const overlayData = Alpine.$data(dragdropOverlay);
            if (overlayData) {
                setTimeout(() => {
                    overlayData.isVisible = false;
                    console.log('🟣 Overlay visibility set to false after timeout');
                }, 300);
            }
        }
    });
    console.log('🟣 Modal drag drop instance created:', !!this._modalDragDropInstance);
  },

  cleanupDragAndDrop() {
    console.log('🔴 cleanupDragAndDrop called');
    if (this._modalDragDropInstance) {
        console.log('🔴 Cleaning up modal drag drop instance');
        this._modalDragDropInstance.cleanup();
        this._modalDragDropInstance = null;
    }
    if (this._sidebarDragDropInstance) {
        console.log('🔴 Cleaning up sidebar drag drop instance');
        this._sidebarDragDropInstance.cleanup();
        this._sidebarDragDropInstance = null;
    }
  },

  // Add initialization of drag and drop to the init function
  init() {
    // Watch for modal open/close
    this.$watch('isOpen', async (value) => {
        if (value) {
            await this.fetchFiles(this.browser.currentPath);
            // Setup drag and drop when modal opens
            setTimeout(() => {
                this.setupDragAndDrop();
            }, 100); // Small delay to ensure DOM is ready
        } else {
            // Cleanup drag and drop when modal closes
            this.cleanupDragAndDrop();
        }
    });

    // Ensure cleanup on component destroy
    this.$el._x_cleanups = this.$el._x_cleanups || [];
    this.$el._x_cleanups.push(() => {
        this.cleanupDragAndDrop();
    });

    // Initial file fetch for modal
    this.fetchFiles("$WORK_DIR");
  },

  // Add a new method to refresh both browsers while maintaining their separate contexts
  async refreshBrowsers() {
    // Refresh the modal browser if it's open
    if (this.isOpen) {
      await this.fetchFiles(this.browser.currentPath);
      
      // Update the modal's data using Alpine's reactive data
      const modalEl = document.getElementById('fileBrowserModal');
      if (modalEl && Alpine.$data(modalEl)) {
        const modalData = Alpine.$data(modalEl);
        modalData.browser = {
          ...modalData.browser,
          entries: this.browser.entries,
          currentPath: this.browser.currentPath,
          parentPath: this.browser.parentPath
        };
      }
    }
    
    // Refresh the sidebar browser independently
    const filesSection = Alpine.$data(document.getElementById('files-section'));
    if (filesSection) {
      await filesSection.fetchFiles(filesSection.currentPath);
    }
  }
};

document.addEventListener("alpine:init", () => {
  // File browser modal
  Alpine.data("fileBrowserModalProxy", () => ({
    ...fileBrowserModalProxy,
    init() {
      // Watch for modal open/close
      this.$watch("isOpen", async (value) => {
        if (value) {
          await this.fetchFiles(this.browser.currentPath);
          // Setup drag and drop when modal opens
          this.setupDragAndDrop();
        } else {
          // Cleanup drag and drop when modal closes
          this.cleanupDragAndDrop();
        }
      });

      // Initial file fetch
      this.fetchFiles("$WORK_DIR");
    }
  }));
});

// Remove the alpine:initialized event listener since we handle initialization in Alpine.data
window.fileBrowserModalProxy = fileBrowserModalProxy;
fileBrowserModalProxy.handleFileUpload = fileBrowserModalProxy.handleFileUpload.bind(fileBrowserModalProxy);

// Add global fetchFiles function for the sidebar
window.fetchFiles = async function(path = "") {
    const filesSection = document.getElementById('files-section');
    if (!filesSection) return;
    
    const component = Alpine.$data(filesSection);
    if (!component) return;
    
    await component.fetchFiles(path);
};

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
