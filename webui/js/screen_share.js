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
        this.isControlActive = false;
    },

    /* ------------------------------------------------------------------
     * THROTTLE UTILITY FUNCTION
     * ------------------------------------------------------------------ */
    throttle(func, limit) {
        let lastFunc;
        let lastRan;
        return function(...args) {
            const context = this;
            if (!lastRan) {
                func.apply(context, args);
                lastRan = Date.now();
            } else {
                clearTimeout(lastFunc);
                lastFunc = setTimeout(function() {
                    if ((Date.now() - lastRan) >= limit) {
                        func.apply(context, args);
                        lastRan = Date.now();
                    }
                }, limit - (Date.now() - lastRan));
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
        this.throttledHandleMouseMove = this.throttle(this.handleMouseMove.bind(this), 100); // Throttle to 100ms
        this.throttledHandleMouseDown = this.handleMouseDown.bind(this);
        this.throttledHandleMouseUp = this.handleMouseUp.bind(this);
        this.throttledHandleKeyDown = this.handleKeyDown.bind(this);
        this.throttledHandleKeyUp = this.handleKeyUp.bind(this);

        // Attach the throttled mouse event handlers to the screen-share-stream element
        screenShareStreamEl.addEventListener('mousemove', this.throttledHandleMouseMove);
        screenShareStreamEl.addEventListener('mousedown', this.throttledHandleMouseDown);
        screenShareStreamEl.addEventListener('mouseup', this.throttledHandleMouseUp);

        // Attach keyboard event handlers to the document if needed
        // Uncomment the following lines if you want keyboard events to remain global
        // document.addEventListener('keydown', this.throttledHandleKeyDown);
        // document.addEventListener('keyup', this.throttledHandleKeyUp);
    },

    removeControlListeners() {
        const screenShareStreamEl = document.getElementById('screen-share-stream');
        if (!screenShareStreamEl) {
            console.error('Screen share stream element not found');
            return;
        }

        // Remove the throttled mouse event handlers from the screen-share-stream element
        if (this.throttledHandleMouseMove) {
            screenShareStreamEl.removeEventListener('mousemove', this.throttledHandleMouseMove);
            this.throttledHandleMouseMove = null;
        }
        if (this.throttledHandleMouseDown) {
            screenShareStreamEl.removeEventListener('mousedown', this.throttledHandleMouseDown);
            this.throttledHandleMouseDown = null;
        }
        if (this.throttledHandleMouseUp) {
            screenShareStreamEl.removeEventListener('mouseup', this.throttledHandleMouseUp);
            this.throttledHandleMouseUp = null;
        }

        // Remove keyboard event handlers from the document if they were attached
        // Uncomment the following lines if you attached keyboard events globally
        // if (this.throttledHandleKeyDown) {
        //     document.removeEventListener('keydown', this.throttledHandleKeyDown);
        //     this.throttledHandleKeyDown = null;
        // }
        // if (this.throttledHandleKeyUp) {
        //     document.removeEventListener('keyup', this.throttledHandleKeyUp);
        //     this.throttledHandleKeyUp = null;
        // }
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
