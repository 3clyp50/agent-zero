const screenShareModalProxy = {
    isOpen: false,
    isLoading: false,
    streamInterval: null,

    async openModal() {
        const modalEl = document.getElementById('screenShareModal');
        const modalAD = Alpine.$data(modalEl);

        modalAD.isOpen = true;
        modalAD.isLoading = true;

        await modalAD.startFetchingFrames();
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
    }
};

document.addEventListener('alpine:init', () => {
    Alpine.data('screenShareModalProxy', () => ({
        init() {
            Object.assign(this, screenShareModalProxy);
            // Ensure immediate frame fetch when modal opens
            this.$watch('isOpen', async (value) => {
                if (value) {
                    await this.startFetchingFrames();
                }
            });
        }
    }));
});

// Assign the proxy to the window object for global access
window.screenShareModalProxy = screenShareModalProxy;
