const screenShareModalProxy = {
    isOpen: false,
    isLoading: false,
    streamInterval: null,
    aspectRatio: 3 / 2, // Define your desired aspect ratio (width / height)

    // New state for controlling the session
    isControlActive: false,

    // Throttled event handlers
    throttledHandleMouseMove: null,
    throttledHandleMouseDown: null,
    throttledHandleMouseUp: null,
    throttledHandleKeyDown: null,
    throttledHandleKeyUp: null,

    // Throttled overlay event handlers
    throttledHandleKeyDownOverlay: null,
    throttledHandleKeyUpOverlay: null,

    // Store the context menu listener
    contextMenuListener: null,

    async toggleModal() {
        if (this.isOpen) {
            this.closeModal();
        } else {
            await this.openModal();
        }
    },

    async openModal() {
        const modalEl = document.getElementById('screenShareModal');
        if (!modalEl) {
            console.error('Modal element with ID "screenShareModal" not found.');
            return;
        }

        const modalAD = Alpine.$data(modalEl);
        modalAD.isOpen = true;
        modalAD.isLoading = true;

        this.initDraggable();
        this.initResizable();
        await this.startFetchingFrames();

        // Show the keyboard overlay
        const overlay = document.getElementById('screen-share-overlay');
        if (overlay) {
            overlay.style.display = 'block';
        }

        // Focus the modal
        modalEl.setAttribute('tabindex', '-1'); // Ensure it's focusable
        modalEl.focus();
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
                    this.streamInterval = setTimeout(fetchFrame, 100);
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
        // If control is active, stop it before closing
        if (this.isControlActive) {
            this.stopControl();
        }

        const modalEl = document.getElementById('screenShareModal');
        if (!modalEl) {
            console.error('Modal element with ID "screenShareModal" not found.');
            return;
        }
        const modalAD = Alpine.$data(modalEl);
        modalAD.isOpen = false;

        this.stopFetchingFrames();

        // Hide the keyboard overlay
        const overlay = document.getElementById('screen-share-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    },

    initDraggable() {
        const headerEl = document.getElementById('screen-share-header');
        const containerEl = document.getElementById('screen-share-window');
        if (!headerEl || !containerEl) {
            console.error("Draggable elements not found");
            return;
        }

        let isDragging = false;
        let startX = 0, startY = 0;
        let initialLeft = 0, initialTop = 0;

        headerEl.addEventListener('mousedown', (e) => {
            // Only respond to left mouse button
            if (e.button !== 0) return;

            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;

            const rect = containerEl.getBoundingClientRect();
            initialLeft = rect.left;
            initialTop = rect.top;

            e.preventDefault(); // Prevent text selection
        });

        const onMouseMove = (e) => {
            if (!isDragging) return;

            const dx = e.clientX - startX;
            const dy = e.clientY - startY;

            let newLeft = initialLeft + dx;
            let newTop = initialTop + dy;

            const windowWidth = window.innerWidth;
            const windowHeight = window.innerHeight;
            const rect = containerEl.getBoundingClientRect();
            const modalWidth = rect.width;
            const modalHeight = rect.height;

            if (newLeft < 0) newLeft = 0;
            if (newLeft + modalWidth > windowWidth) {
                newLeft = windowWidth - modalWidth;
            }
            if (newTop < 0) newTop = 0;
            if (newTop + modalHeight > windowHeight) {
                newTop = windowHeight - modalHeight;
            }

            containerEl.style.left = `${newLeft}px`;
            containerEl.style.top = `${newTop}px`;
        };

        const onMouseUp = () => {
            isDragging = false;
        };

        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);

        // Cleanup when modal closes
        Alpine.effect(() => {
            if (!this.isOpen) {
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            }
        });
    },

    initResizable() {
        const containerEl = document.getElementById('screen-share-window');
        if (!containerEl) {
            console.error('Screen share window element not found');
            return;
        }

        const resizer = containerEl.querySelector('.resize-handle');
        if (!resizer) {
            console.error('Resize handle not found');
            return;
        }

        let isResizing = false;
        let lastX = 0;
        let lastY = 0;
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

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });

        const onMouseMove = (e) => {
            if (!isResizing) return;

            const dx = e.clientX - lastX;
            let newWidth = startWidth + dx;
            let newHeight = newWidth / this.aspectRatio;

            // Enforce min/max
            if (newWidth < 500) {
                newWidth = 500;
                newHeight = newWidth / this.aspectRatio;
            } else if (newWidth > 1350) {
                newWidth = 1350;
                newHeight = newWidth / this.aspectRatio;
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

        // Cleanup if modal closes
        Alpine.effect(() => {
            if (!this.isOpen) {
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            }
        });
    },

    /* ------------------------------------------------------------------
     * METHODS FOR TAKING CONTROL & STOPPING CONTROL
     * ------------------------------------------------------------------ */
    async toggleControl() {
        if (this.isControlActive) {
            this.stopControl();
        } else {
            await this.startControl();
        }
    },

    async startControl() {
        // 1) Attempt to make the modal fullscreen
        const containerEl = document.getElementById('screen-share-window');
        if (!containerEl) return;

        // Some browsers require calling .requestFullscreen() on the element
        try {
            if (containerEl.requestFullscreen) {
                await containerEl.requestFullscreen();
            } else if (containerEl.webkitRequestFullscreen) {
                // Safari
                await containerEl.webkitRequestFullscreen();
            } else if (containerEl.msRequestFullscreen) {
                // IE/Edge
                await containerEl.msRequestFullscreen();
            }
        } catch (err) {
            console.error("Failed to request fullscreen:", err);
        }

        // 2) Start sending mouse & keyboard events to the backend
        this.addControlListeners();
        this.initOverlay(); // Initialize overlay
        this.isControlActive = true;
    },

    stopControl() {
        // 1) Exit fullscreen if needed
        if (document.fullscreenElement) {
            document.exitFullscreen().catch(err =>
                console.error("Failed to exit fullscreen:", err)
            );
        }

        // 2) Stop sending events to backend
        this.removeControlListeners();
        this.removeOverlayListeners(); // Remove overlay listeners
        this.isControlActive = false;
    },

    /* ------------------------------------------------------------------
     * THROTTLE UTILITY FUNCTION
     * ------------------------------------------------------------------ */
    throttle(func, limit) {
        let inThrottle = false;
        return function (...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /* ------------------------------------------------------------------
     * EVENT LISTENER ATTACHMENT AND REMOVAL
     * ------------------------------------------------------------------ */
    addControlListeners() {
        const screenShareStreamEl = document.getElementById('screen-share-stream');
        if (!screenShareStreamEl) {
            console.error('Screen share stream element not found');
            return;
        }

        // Create throttled versions of the event handlers
        if (!this.throttledHandleMouseMove) {
            this.throttledHandleMouseMove = this.throttle(this.handleMouseMove.bind(this), 100); // Throttle to 100ms
        }
        if (!this.throttledHandleMouseDown) {
            this.throttledHandleMouseDown = this.throttle(this.handleMouseDown.bind(this), 0); // Optional throttling
        }
        if (!this.throttledHandleMouseUp) {
            this.throttledHandleMouseUp = this.throttle(this.handleMouseUp.bind(this), 0); // Optional throttling
        }
        if (!this.throttledHandleKeyDown) {
            this.throttledHandleKeyDown = this.throttle(this.handleKeyDown.bind(this), 0); // Optional throttling
        }
        if (!this.throttledHandleKeyUp) {
            this.throttledHandleKeyUp = this.throttle(this.handleKeyUp.bind(this), 0); // Optional throttling
        }

        // Attach the throttled mouse event handlers to the screen-share-stream element in capture phase
        screenShareStreamEl.addEventListener('mousemove', this.throttledHandleMouseMove, true); // Use capture
        screenShareStreamEl.addEventListener('mousedown', this.throttledHandleMouseDown, true);
        screenShareStreamEl.addEventListener('mouseup', this.throttledHandleMouseUp, true);

        // Define and store the context menu listener
        this.contextMenuListener = (e) => {
            e.preventDefault();
            e.stopPropagation();
            // Optionally, send context menu event to backend if needed
        };
        screenShareStreamEl.addEventListener('contextmenu', this.contextMenuListener, true);

        // Attach keyboard event handlers to the document using capture phase
        document.addEventListener('keydown', this.throttledHandleKeyDown, true); // Use capture
        document.addEventListener('keyup', this.throttledHandleKeyUp, true); // Use capture
    },

    removeControlListeners() {
        const screenShareStreamEl = document.getElementById('screen-share-stream');
        if (!screenShareStreamEl) {
            console.error('Screen share stream element not found');
            return;
        }

        // Remove the throttled mouse event handlers from the screen-share-stream element
        if (this.throttledHandleMouseMove) {
            screenShareStreamEl.removeEventListener('mousemove', this.throttledHandleMouseMove, true);
        }
        if (this.throttledHandleMouseDown) {
            screenShareStreamEl.removeEventListener('mousedown', this.throttledHandleMouseDown, true);
        }
        if (this.throttledHandleMouseUp) {
            screenShareStreamEl.removeEventListener('mouseup', this.throttledHandleMouseUp, true);
        }

        // Remove the context menu listener if it exists
        if (this.contextMenuListener) {
            screenShareStreamEl.removeEventListener('contextmenu', this.contextMenuListener, true);
            this.contextMenuListener = null;
        }

        // Remove keyboard event handlers from the document
        if (this.throttledHandleKeyDown) {
            document.removeEventListener('keydown', this.throttledHandleKeyDown, true);
        }
        if (this.throttledHandleKeyUp) {
            document.removeEventListener('keyup', this.throttledHandleKeyUp, true);
        }

        // Reset the throttled handlers
        this.throttledHandleMouseMove = null;
        this.throttledHandleMouseDown = null;
        this.throttledHandleMouseUp = null;
        this.throttledHandleKeyDown = null;
        this.throttledHandleKeyUp = null;
    },

    /* ------------------------------------------------------------------
     * OVERLAY EVENT LISTENER ATTACHMENT AND REMOVAL
     * ------------------------------------------------------------------ */
    initOverlay() {
        const overlay = document.getElementById('screen-share-overlay');
        if (!overlay) {
            console.error('Overlay element with ID "screen-share-overlay" not found.');
            return;
        }

        // Create throttled versions of the event handlers
        if (!this.throttledHandleKeyDownOverlay) {
            this.throttledHandleKeyDownOverlay = this.throttle(this.handleKeyDown.bind(this), 0);
        }
        if (!this.throttledHandleKeyUpOverlay) {
            this.throttledHandleKeyUpOverlay = this.throttle(this.handleKeyUp.bind(this), 0);
        }

        overlay.addEventListener('keydown', this.throttledHandleKeyDownOverlay, true); // Use capture
        overlay.addEventListener('keyup', this.throttledHandleKeyUpOverlay, true); // Use capture

        // Prevent focus from moving to underlying elements
        overlay.setAttribute('tabindex', '0');
        overlay.focus();
    },

    removeOverlayListeners() {
        const overlay = document.getElementById('screen-share-overlay');
        if (!overlay) {
            console.error('Overlay element with ID "screen-share-overlay" not found.');
            return;
        }

        if (this.throttledHandleKeyDownOverlay) {
            overlay.removeEventListener('keydown', this.throttledHandleKeyDownOverlay, true);
            this.throttledHandleKeyDownOverlay = null;
        }
        if (this.throttledHandleKeyUpOverlay) {
            overlay.removeEventListener('keyup', this.throttledHandleKeyUpOverlay, true);
            this.throttledHandleKeyUpOverlay = null;
        }
    },

    /* ------------------------------------------------------------------
     * HELPER FUNCTION TO NORMALIZE Coordinates
     * ------------------------------------------------------------------ */
    getNormalizedCoordinates(e) {
        const img = document.getElementById('screen-share-stream');
        if (!img) {
            console.error('Screen share image element not found');
            return { x: 0, y: 0 };
        }

        const rect = img.getBoundingClientRect();

        // Calculate relative position
        let x = (e.clientX - rect.left) / rect.width;
        let y = (e.clientY - rect.top) / rect.height;

        // Clamp values between 0 and 1
        x = Math.max(0, Math.min(1, x));
        y = Math.max(0, Math.min(1, y));

        return { x, y };
    },

    /* ------------------------------------------------------------------
     * EXAMPLE EVENT HANDLERS WITH Normalized Coordinates
     * ------------------------------------------------------------------ */
    handleMouseMove(e) {
        // Prevent default actions and stop propagation
        e.preventDefault();
        e.stopPropagation();

        const { x, y } = this.getNormalizedCoordinates(e);

        // Example: send "mouse move" events to the backend
        fetch('/share_mouse_event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'move',
                x: x,
                y: y
            })
        }).catch((err) => console.error(err));
    },

    handleMouseDown(e) {
        // Prevent default actions and stop propagation
        e.preventDefault();
        e.stopPropagation();

        const { x, y } = this.getNormalizedCoordinates(e);

        // Example: send "mouse down" with button info
        let button = 'left';
        if (e.button === 1) button = 'middle';
        if (e.button === 2) button = 'right';

        fetch('/share_mouse_event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'down',
                button: button,
                x: x,
                y: y
            })
        }).catch((err) => console.error(err));
    },

    handleMouseUp(e) {
        // Prevent default actions and stop propagation
        e.preventDefault();
        e.stopPropagation();

        const { x, y } = this.getNormalizedCoordinates(e);

        // Example: send "mouse up" with button info
        let button = 'left';
        if (e.button === 1) button = 'middle';
        if (e.button === 2) button = 'right';

        fetch('/share_mouse_event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'up',
                button: button,
                x: x,
                y: y
            })
        }).catch((err) => console.error(err));
    },

    handleKeyDown(e) {
        // Prevent default actions and stop propagation
        e.preventDefault();
        e.stopPropagation();

        // Optionally, handle specific keys
        if (e.key === 'Escape') {
            // Do nothing or handle differently
            return;
        }

        // Example: send "key down"
        fetch('/share_keyboard_event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'keydown',
                key: e.key
            })
        }).catch((err) => console.error(err));
    },

    handleKeyUp(e) {
        // Prevent default actions and stop propagation
        e.preventDefault();
        e.stopPropagation();

        // Example: send "key up"
        fetch('/share_keyboard_event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'keyup',
                key: e.key
            })
        }).catch((err) => console.error(err));
    },
};

// Attach to the global window object (if desired)
window.screenShareModalProxy = screenShareModalProxy;
