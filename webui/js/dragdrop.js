/**
 * Reusable drag-and-drop module for handling file uploads across different contexts
 * in the application. This module provides a consistent interface for managing drag
 * and drop events, overlay visibility, and file handling.
 */

const DragDropManager = {
    /**
     * Creates a new drag-and-drop instance with the specified configuration
     * @param {Object} config Configuration object
     * @param {HTMLElement} config.container The container element to attach drag-drop events to
     * @param {HTMLElement} config.overlay The overlay element to show during drag
     * @param {Function} config.onDrop Callback function called when files are dropped
     * @param {Function} [config.onDragStart] Optional callback when drag enters the container
     * @param {Function} [config.onDragEnd] Optional callback when drag leaves the container
     * @param {boolean} [config.useCapture=false] Whether to use capture phase for events
     * @param {HTMLElement} [config.globalOverlay] Optional global overlay to hide during modal drag
     * @returns {Object} Instance with cleanup method
     */
    create(config) {
        console.log('🟢 DragDropManager.create called with config:', {
            hasContainer: !!config.container,
            hasOverlay: !!config.overlay,
            hasOnDrop: !!config.onDrop,
            useCapture: config.useCapture,
            hasGlobalOverlay: !!config.globalOverlay
        });

        const {
            container,
            overlay,
            onDrop,
            onDragStart,
            onDragEnd,
            useCapture = false,
            globalOverlay
        } = config;

        let dragCounter = 0;
        
        // Get Alpine data for overlay visibility management
        const overlayData = Alpine.$data(overlay);
        console.log('🟢 Overlay Alpine data found:', !!overlayData);

        const handleDragEnter = (e) => {
            console.log('🟢 DragEnter event triggered', {
                target: e.target.className,
                currentTarget: e.currentTarget.className,
                counter: dragCounter,
                dataTransfer: e.dataTransfer?.types
            });
            
            // Prevent event from bubbling to parent containers
            e.preventDefault();
            e.stopPropagation();

            // Check if we're dragging from/to the overlay itself
            const isFromOverlay = e.relatedTarget && (
                e.relatedTarget === overlay ||
                overlay.contains(e.relatedTarget)
            );

            // Only increment if not coming from overlay
            if (!isFromOverlay) {
                dragCounter++;
                
                if (dragCounter === 1) {
                    console.log('🟢 First drag enter, showing overlay');
                    // Hide global overlay if we're in a modal context
                    if (globalOverlay) {
                        const globalOverlayData = Alpine.$data(globalOverlay);
                        globalOverlayData.isVisible = false;
                        console.log('🟢 Global overlay hidden');
                    }
                    
                    // Show our context overlay
                    if (overlayData) {
                        overlayData.isVisible = true;
                        console.log('🟢 Overlay visibility set to true');
                    }
                    
                    // Call optional dragStart callback
                    if (onDragStart) {
                        console.log('🟢 Calling onDragStart callback');
                        onDragStart();
                    }
                }
            }
        };

        const handleDragOver = (e) => {
            e.preventDefault();
            e.stopPropagation();
        };

        const handleDragLeave = (e) => {
            console.log('🟢 DragLeave event triggered', {
                target: e.target.className,
                currentTarget: e.currentTarget.className,
                counter: dragCounter,
                relatedTarget: e.relatedTarget?.className
            });
            
            // Prevent event from bubbling to parent containers
            e.preventDefault();
            e.stopPropagation();

            // Check if we're dragging to the overlay itself
            const isToOverlay = e.relatedTarget && (
                e.relatedTarget === overlay ||
                overlay.contains(e.relatedTarget)
            );

            // Only decrement if not going to overlay
            if (!isToOverlay) {
                dragCounter--;
                
                if (dragCounter === 0) {
                    console.log('🟢 Last drag leave, hiding overlay');
                    if (overlayData) {
                        overlayData.isVisible = false;
                        console.log('🟢 Overlay hidden after transition');
                    }
                    
                    // Call optional dragEnd callback
                    if (onDragEnd) {
                        console.log('🟢 Calling onDragEnd callback');
                        onDragEnd();
                    }
                }
            }
        };

        const handleDrop = async (e) => {
            console.log('🟢 Drop event triggered');
            e.preventDefault();
            e.stopPropagation();
            
            dragCounter = 0;
            
            // Hide overlay immediately
            if (overlayData) {
                overlayData.isVisible = false;
                console.log('🟢 Overlay hidden immediately after drop');
            }
            overlay.classList.remove('active');
            
            // Hide global overlay if present
            if (globalOverlay) {
                const globalOverlayData = Alpine.$data(globalOverlay);
                if (globalOverlayData) {
                    globalOverlayData.isVisible = false;
                    console.log('🟢 Global overlay hidden after drop');
                }
                globalOverlay.classList.remove('active');
            }

            // Convert FileList to Array and call the drop handler
            const files = Array.from(e.dataTransfer.files);
            console.log('🟢 Processing drop with files:', files.length);
            if (files.length > 0) {
                await onDrop(files);
            }
            
            // Call optional dragEnd callback
            if (onDragEnd) {
                console.log('🟢 Calling onDragEnd callback after drop');
                onDragEnd();
            }
        };

        console.log('🟢 Setting up event listeners on container');
        // Attach event listeners
        container.addEventListener('dragenter', handleDragEnter, useCapture);
        container.addEventListener('dragover', handleDragOver, useCapture);
        container.addEventListener('dragleave', handleDragLeave, useCapture);
        container.addEventListener('drop', handleDrop, useCapture);

        // Return cleanup function
        return {
            cleanup() {
                console.log('🟢 Cleaning up drag drop instance');
                container.removeEventListener('dragenter', handleDragEnter, useCapture);
                container.removeEventListener('dragover', handleDragOver, useCapture);
                container.removeEventListener('dragleave', handleDragLeave, useCapture);
                container.removeEventListener('drop', handleDrop, useCapture);
                
                // Reset counter and ensure overlay is hidden
                dragCounter = 0;
                overlay.classList.remove('active');
                if (overlayData) {
                    overlayData.isVisible = false;
                }
                console.log('🟢 Drag drop cleanup completed');
            }
        };
    },

    /**
     * Helper function to create a file upload event object
     * @param {File[]} files Array of files to upload
     * @param {string} source Identifier for upload source ('modal' or 'sidebar')
     * @returns {Object} Event-like object for file upload handling
     */
    createUploadEvent(files, source) {
        console.log('🟢 Creating upload event for source:', source, 'with files:', files.length);
        return {
            target: {
                files,
                getAttribute: () => source
            }
        };
    }
};

// Export for use in other modules
window.DragDropManager = DragDropManager; 