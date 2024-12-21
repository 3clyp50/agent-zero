// screen_share.js

const screenShareModalProxy = {
    isOpen: false,
    isLoading: false,
    streamInterval: null,

    async toggleModal() {
        if (this.isOpen) {
            this.handleClose();
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

    handleClose() {
        this.isOpen = false;
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
};

// Attach to the global window object
window.screenShareModalProxy = screenShareModalProxy;
