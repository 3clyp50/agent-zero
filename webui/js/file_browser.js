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

    // Setup drag and drop handlers when modal opens
    this.setupDragAndDrop();
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
    const modalEl = document.getElementById('fileBrowserModal');
    if (!modalEl) return;
    const modalContent = modalEl.querySelector('.modal-content');
    const dragdropOverlay = modalEl.querySelector('.files-dragdrop-overlay');
    if (!modalContent || !dragdropOverlay) return;
    
    this._dragCounter = 0;

    const handleDragEnter = (e) => {
      e.preventDefault();
      e.stopPropagation();  // Prevent event from reaching the body
      this._dragCounter++;
      if (this._dragCounter === 1) {
        // Hide the main overlay first
        const mainOverlay = document.getElementById('dragdrop-overlay');
        if (mainOverlay) {
          const mainOverlayData = Alpine.$data(mainOverlay);
          mainOverlayData.isVisible = false;
        }
        // Show our modal overlay
        const overlayData = Alpine.$data(dragdropOverlay);
        overlayData.isVisible = true;
        dragdropOverlay.classList.add('active');
      }
    };

    const handleDragOver = (e) => {
      e.preventDefault();
      e.stopPropagation();  // Prevent event from reaching the body
    };

    const handleDragLeave = (e) => {
      e.preventDefault();
      e.stopPropagation();  // Prevent event from reaching the body
      this._dragCounter--;
      if (this._dragCounter === 0) {
        const overlayData = Alpine.$data(dragdropOverlay);
        overlayData.isVisible = false;
        dragdropOverlay.classList.remove('active');
      }
    };

    const handleDrop = async (e) => {
      e.preventDefault();
      e.stopPropagation();  // Prevent event from reaching the body
      this._dragCounter = 0;
      const overlayData = Alpine.$data(dragdropOverlay);
      overlayData.isVisible = false;
      dragdropOverlay.classList.remove('active');

      // Hide the main chat overlay as well
      const mainOverlay = document.getElementById('dragdrop-overlay');
      if (mainOverlay) {
        const mainOverlayData = Alpine.$data(mainOverlay);
        mainOverlayData.isVisible = false;
        mainOverlay.classList.remove('active');
      }

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        // Add data-upload-source to indicate this is from the modal
        await this.handleFileUpload({ 
          target: { 
            files,
            getAttribute: () => 'modal' 
          } 
        });
      }
    };

    // Attach listeners to the modal-content element
    modalContent.addEventListener('dragenter', handleDragEnter, true);
    modalContent.addEventListener('dragover', handleDragOver, true);
    modalContent.addEventListener('dragleave', handleDragLeave, true);
    modalContent.addEventListener('drop', handleDrop, true);
    
    // Store handlers for cleanup
    this._boundHandlers = {
      dragenter: handleDragEnter,
      dragover: handleDragOver,
      dragleave: handleDragLeave,
      drop: handleDrop
    };
  },

  cleanupDragAndDrop() {
    const modalEl = document.getElementById('fileBrowserModal');
    if (!modalEl) return;
    const modalContent = modalEl.querySelector('.modal-content');
    if (modalContent && this._boundHandlers) {
      modalContent.removeEventListener('dragenter', this._boundHandlers.dragenter);
      modalContent.removeEventListener('dragover', this._boundHandlers.dragover);
      modalContent.removeEventListener('dragleave', this._boundHandlers.dragleave);
      modalContent.removeEventListener('drop', this._boundHandlers.drop);
    }
  },

  // Add initialization of drag and drop to the init function
  init() {
    // Watch for modal open/close
    this.$watch('isOpen', (value) => {
      if (value) {
        this.setupDragAndDrop();
      } else {
        this.cleanupDragAndDrop();
      }
    });
  },

  setupModalDragAndDrop() {
    const modalContainer = document.getElementById('fileBrowserModal');
    const dragdropOverlay = document.querySelector('.files-dragdrop-overlay');
    
    if (!modalContainer || !dragdropOverlay) return;
    
    this._modalDragCounter = 0;
    
    const handleDragEnter = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this._modalDragCounter++;
      if (this._modalDragCounter === 1) {
        const overlayData = Alpine.$data(dragdropOverlay);
        overlayData.isVisible = true;
        dragdropOverlay.classList.add('active');
      }
    };
    
    const handleDragOver = (e) => {
      e.preventDefault();
      e.stopPropagation();
    };
    
    const handleDragLeave = (e) => {
      e.preventDefault();
      e.stopPropagation();
      this._modalDragCounter--;
      if (this._modalDragCounter === 0) {
        const overlayData = Alpine.$data(dragdropOverlay);
        overlayData.isVisible = false;
        dragdropOverlay.classList.remove('active');
      }
    };
    
    const handleDrop = async (e) => {
      e.preventDefault();
      e.stopPropagation();
      this._modalDragCounter = 0;
      const overlayData = Alpine.$data(dragdropOverlay);
      overlayData.isVisible = false;
      dragdropOverlay.classList.remove('active');
      
      // Hide the main chat overlay as well
      const mainOverlay = document.getElementById('dragdrop-overlay');
      if (mainOverlay) {
        const mainOverlayData = Alpine.$data(mainOverlay);
        mainOverlayData.isVisible = false;
        mainOverlay.classList.remove('active');
      }
      
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        await this.handleFileUpload({ target: { files } });
      }
    };
    
    // Add event listeners to the entire modal container
    modalContainer.addEventListener('dragenter', handleDragEnter);
    modalContainer.addEventListener('dragover', handleDragOver);
    modalContainer.addEventListener('dragleave', handleDragLeave);
    modalContainer.addEventListener('drop', handleDrop);
    
    // Store handlers for cleanup
    this._modalBoundHandlers = {
      dragenter: handleDragEnter,
      dragover: handleDragOver,
      dragleave: handleDragLeave,
      drop: handleDrop
    };
  },

  cleanupModalDragAndDrop() {
    const modalContainer = document.getElementById('fileBrowserModal');
    const filesList = modalContainer?.querySelector('.files-list');
    
    if (filesList && this._modalBoundHandlers) {
      filesList.removeEventListener('dragenter', this._modalBoundHandlers.dragenter);
      filesList.removeEventListener('dragover', this._modalBoundHandlers.dragover);
      filesList.removeEventListener('dragleave', this._modalBoundHandlers.dragleave);
      filesList.removeEventListener('drop', this._modalBoundHandlers.drop);
    }
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
    init() {
      Object.assign(this, fileBrowserModalProxy);
      
      // Replace modal-specific drag and drop with the working global version
      this.$watch("isOpen", async (value) => {
        if (value) {
          await this.fetchFiles(this.browser.currentPath);
          // Setup drag and drop when modal opens using the working method
          this.setupDragAndDrop();
        } else {
          // Cleanup drag and drop when modal closes using the working method
          this.cleanupDragAndDrop();
        }
      });

      // Initial file fetch for modal
      this.fetchFiles("$WORK_DIR");
    },
  }));
});

// Keep the global assignment for backward compatibility
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
