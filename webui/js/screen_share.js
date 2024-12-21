// screen_share.js

const screenShareModalProxy = {
    isOpen: false,
    isLoading: false,
    streamInterval: null,
    aspectRatio: 3 / 2, // Define your desired aspect ratio (width / height)

    async toggleModal() {
        if (this.isOpen) {
            this.closeModal();
        } else {
            await this.openModal();
        }
    },

    async openModal() {
        const modalEl = document.getElementById('screenShareModal');
        const modalAD = Alpine.$data(modalEl);

        if (!modalEl) {
            console.error('Modal element with ID "screenShareModal" not found.');
            return;
        }

        modalAD.isOpen = true;
        modalAD.isLoading = true;

        this.initDraggable();
        this.initResizable();

        await this.startFetchingFrames();
    },

    async startFetchingFrames() {
        const img = document.getElementById('screen-share-stream');
        if (!img) {
            console.error('Screen share image element not found');
            return;
        }

        const fetchFrame = async () => {
            try {
                const response = await fetch('/get_screen_frame');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                if (data.frame) {
                    img.src = 'data:image/jpeg;base64,' + data.frame;
                } else {
                    console.warn('No frame data received');
                }
            } catch (error) {
                console.error('Error fetching frame:', error);
            } finally {
                // Continue fetching frames if the modal is still open
                if (this.isOpen) {
                    this.streamInterval = setTimeout(fetchFrame, 100); // Fetch next frame after 100ms
                }
            }
        };

        fetchFrame();
    },

    stopFetchingFrames() {
        if (this.streamInterval) {
            clearTimeout(this.streamInterval);
            this.streamInterval = null;
        }
        const img = document.getElementById('screen-share-stream');
        if (img) {
            img.src = '';
        }
    },

    closeModal() {
        const modalEl = document.getElementById('screenShareModal');
        const modalAD = Alpine.$data(modalEl);

        if (!modalEl) {
            console.error('Modal element with ID "screenShareModal" not found.');
            return;
        }

        modalAD.isOpen = false;

        this.stopFetchingFrames();
    },

    initDraggable() {
        const modalEl = document.getElementById('screenShareModal');
        if (!modalEl) {
            console.error('Modal element with ID "screenShareModal" not found.');
            return;
        }

        // Query the .modal-header within the modal
        const headerEl = document.getElementById('screen-share-header');
        const containerEl = document.getElementById('screen-share-window');

        if (!headerEl) {
            console.error("Could not find .modal-header element");
            return;
        }

        if (!containerEl) {
            console.error("Could not find .screen-share-window element");
            return;
        }

        let isDragging = false;
        let startX = 0, startY = 0;
        let initialLeft = 0, initialTop = 0;

        headerEl.addEventListener('mousedown', (e) => {
            // Only respond to left mouse button (button=0)
            if (e.button !== 0) return;

            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;

            const rect = containerEl.getBoundingClientRect();
            initialLeft = rect.left;
            initialTop = rect.top;

            // Prevent text selection
            e.preventDefault();
        });

        // Listen on document for mousemove and mouseup
        const onMouseMove = (e) => {
            if (!isDragging) return;

            const dx = e.clientX - startX;
            const dy = e.clientY - startY;

            containerEl.style.left = (initialLeft + dx) + 'px';
            containerEl.style.top = (initialTop + dy) + 'px';
        };

        const onMouseUp = () => {
            isDragging = false;
        };

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);

        // Cleanup if modal closes or Alpine unmounts
        Alpine.effect(() => {
            if (!this.isOpen) {
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            }
        });
    },

    initResizable() {
        const containerEl = document.getElementById('screen-share-window');
        const resizer = containerEl.querySelector('.resize-handle');
        if (!resizer) {
            console.error('Resize handle not found');
            return;
        }

        let isResizing = false;
        let lastX = 0;
        let lastY = 0;

        // Store the initial dimensions
        let startWidth = 0;
        let startHeight = 0;

        resizer.addEventListener('mousedown', (e) => {
            e.preventDefault();
            isResizing = true;
            lastX = e.clientX;
            lastY = e.clientY;
            const rect = containerEl.getBoundingClientRect();
            startWidth = rect.width;
            startHeight = rect.height;

            // Add listeners for mousemove and mouseup
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });

        const onMouseMove = (e) => {
            if (!isResizing) return;

            const dx = e.clientX - lastX;
            const dy = e.clientY - lastY;

            // Determine whether to use dx or dy based on aspect ratio
            // Calculate potential new width and height
            let newWidth = startWidth + dx;
            let newHeight = newWidth / this.aspectRatio;

            if (newWidth < 500 || newWidth > 1350) {
                return
            }

            containerEl.style.width = `${newWidth}px`;
            containerEl.style.height = `${newHeight}px`;
        };

        const onMouseUp = () => {
            if (isResizing) {
                isResizing = false;
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            }
        };

        // Cleanup if modal closes or Alpine unmounts
        Alpine.effect(() => {
            if (!this.isOpen) {
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            }
        });
    },
};

// Attach to the global window object
window.screenShareModalProxy = screenShareModalProxy;
