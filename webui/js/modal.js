const fullScreenInputModalProxy = {
    isOpen: false,
    inputText: '',
    wordWrap: true,
    undoStack: [],
    redoStack: [],
    maxStackSize: 100,
    lastSavedState: '',
    isCodeMode: false,
    aceEditor: null,
    attachments: [],
    hasAttachments: false,

    openModal() {
        const chatInput = document.getElementById('chat-input');
        const inputSection = document.getElementById('input-section');
        const inputData = Alpine.$data(inputSection);
        
        this.inputText = chatInput.value;
        this.lastSavedState = this.inputText;
        this.isOpen = true;
        this.undoStack = [];
        this.redoStack = [];
        
        // Sync attachments with the main input section
        this.attachments = [...inputData.attachments];
        this.hasAttachments = inputData.hasAttachments;
        
        // Setup drag and drop handlers
        this.setupDragAndDrop();
        
        // Focus the appropriate input after a short delay to ensure the modal is rendered
        setTimeout(() => {
            if (this.isCodeMode) {
                if (!this.aceEditor) {
                    this.initAceEditor();
                }
                this.aceEditor.setValue(this.inputText, -1);
                this.aceEditor.focus();
            } else {
                const fullScreenInput = document.getElementById('full-screen-input');
                fullScreenInput.focus();
            }
        }, 100);
    },

    handleClose() {
        // Sync attachments back to the main input section
        const inputSection = document.getElementById('input-section');
        const inputData = Alpine.$data(inputSection);
        inputData.attachments = [...this.attachments];
        inputData.hasAttachments = this.hasAttachments;
        
        // Cleanup drag and drop handlers
        this.cleanupDragAndDrop();
        
        // Ensure both overlays are hidden
        const modalDragdropOverlay = document.getElementById('modal-dragdrop-overlay');
        const mainDragdropOverlay = document.getElementById('dragdrop-overlay');
        if (modalDragdropOverlay) {
            const modalOverlayData = Alpine.$data(modalDragdropOverlay);
            modalOverlayData.isVisible = false;
        }
        if (mainDragdropOverlay) {
            const mainOverlayData = Alpine.$data(mainDragdropOverlay);
            mainOverlayData.isVisible = false;
        }
        
        // Reset drag counter
        this._dragCounter = 0;
        
        // Update the main textarea
        const chatInput = document.getElementById('chat-input');
        chatInput.value = this.isCodeMode ? this.aceEditor.getValue() : this.inputText;
        this.isOpen = false;
        
        // Trigger input event to update UI
        chatInput.dispatchEvent(new Event('input', { bubbles: true }));
    },

    setupDragAndDrop() {
        const modalContainer = document.querySelector('.full-screen-input-modal');
        const dragdropOverlay = document.getElementById('modal-dragdrop-overlay');
        const overlayData = Alpine.$data(dragdropOverlay);
        
        modalContainer.addEventListener('dragenter', this.handleDragEnter.bind(this));
        modalContainer.addEventListener('dragover', this.handleDragOver.bind(this));
        modalContainer.addEventListener('dragleave', this.handleDragLeave.bind(this));
        modalContainer.addEventListener('drop', this.handleDrop.bind(this));
        
        this._dragCounter = 0;
        this._boundHandlers = {
            dragenter: this.handleDragEnter.bind(this),
            dragover: this.handleDragOver.bind(this),
            dragleave: this.handleDragLeave.bind(this),
            drop: this.handleDrop.bind(this)
        };
    },

    cleanupDragAndDrop() {
        const modalContainer = document.querySelector('.full-screen-input-modal');
        if (modalContainer && this._boundHandlers) {
            modalContainer.removeEventListener('dragenter', this._boundHandlers.dragenter);
            modalContainer.removeEventListener('dragover', this._boundHandlers.dragover);
            modalContainer.removeEventListener('dragleave', this._boundHandlers.dragleave);
            modalContainer.removeEventListener('drop', this._boundHandlers.drop);
        }
    },

    handleDragEnter(e) {
        e.preventDefault();
        this._dragCounter++;
        if (this._dragCounter === 1) {
            const dragdropOverlay = document.getElementById('modal-dragdrop-overlay');
            const overlayData = Alpine.$data(dragdropOverlay);
            overlayData.isVisible = true;
        }
    },

    handleDragOver(e) {
        e.preventDefault();
    },

    handleDragLeave(e) {
        e.preventDefault();
        this._dragCounter--;
        if (this._dragCounter === 0) {
            const dragdropOverlay = document.getElementById('modal-dragdrop-overlay');
            const overlayData = Alpine.$data(dragdropOverlay);
            overlayData.isVisible = false;
        }
    },

    async handleDrop(e) {
        e.preventDefault();
        this._dragCounter = 0;
        const dragdropOverlay = document.getElementById('modal-dragdrop-overlay');
        const overlayData = Alpine.$data(dragdropOverlay);
        overlayData.isVisible = false;

        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) {
            // Process files directly in the modal
            Array.from(files).forEach(file => {
                const ext = file.name.split('.').pop().toLowerCase();
                const isImage = ['jpg', 'jpeg', 'png', 'bmp'].includes(ext);
                
                if (isImage) {
                    // Handle image preview
                    const reader = new FileReader();
                    reader.onload = e => {
                        this.attachments.push({
                            file: file,
                            url: e.target.result,
                            type: 'image',
                            name: file.name,
                            extension: ext
                        });
                        this.hasAttachments = true;
                    };
                    reader.readAsDataURL(file);
                } else {
                    // Handle other file types
                    this.attachments.push({
                        file: file,
                        type: 'file',
                        name: file.name,
                        extension: ext
                    });
                    this.hasAttachments = true;
                }
            });

            // Sync with main input section immediately
            const inputSection = document.getElementById('input-section');
            const inputData = Alpine.$data(inputSection);
            inputData.attachments = [...this.attachments];
            inputData.hasAttachments = this.hasAttachments;
        }
    },

    handleFileUpload(event) {
        const files = event.target.files;
        
        Array.from(files).forEach(file => {
            const ext = file.name.split('.').pop().toLowerCase();
            const isImage = ['jpg', 'jpeg', 'png', 'bmp'].includes(ext);
            
            if (isImage) {
                // Handle image preview
                const reader = new FileReader();
                reader.onload = e => {
                    this.attachments.push({
                        file: file,
                        url: e.target.result,
                        type: 'image',
                        name: file.name,
                        extension: ext
                    });
                    this.hasAttachments = true;
                };
                reader.readAsDataURL(file);
            } else {
                // Handle other file types
                this.attachments.push({
                    file: file,
                    type: 'file',
                    name: file.name,
                    extension: ext
                });
                this.hasAttachments = true;
            }
        });
    },

    initAceEditor() {
        const container = document.getElementById('ace-editor');
        this.aceEditor = ace.edit(container);
        this.aceEditor.setTheme(localStorage.getItem('darkMode') !== 'false' ? 'ace/theme/github_dark' : 'ace/theme/tomorrow');
        this.aceEditor.session.setMode('ace/mode/text');
        this.aceEditor.setOptions({
            fontSize: '0.955rem',
            fontFamily: "'Roboto Mono', monospace",
            showPrintMargin: false,
            wrap: this.wordWrap,
            tabSize: 4,
            useSoftTabs: true,
            navigateWithinSoftTabs: true,
            enableLiveAutocompletion: false,
            enableBasicAutocompletion: false,
            enableSnippets: false
        });

        // Handle tab key for proper indentation
        this.aceEditor.commands.bindKey({ win: 'Tab', mac: 'Tab' }, (editor) => {
            if (editor.selection.isEmpty()) {
                // If no text is selected, insert spaces
                const cursorPosition = editor.getCursorPosition();
                const line = editor.session.getLine(cursorPosition.row);
                const beforeCursor = line.slice(0, cursorPosition.column);
                
                // If at start of line or only whitespace before cursor, indent
                if (!beforeCursor.trim()) {
                    editor.indent();
                } else {
                    // Insert spaces to reach next tab stop
                    const tabSize = editor.session.getTabSize();
                    const nextTabStop = tabSize - (cursorPosition.column % tabSize);
                    editor.insert(" ".repeat(nextTabStop));
                }
            } else {
                // If text is selected, indent the selected lines
                editor.indent();
            }
            return true; // Prevent default
        });

        // Handle Shift+Tab for unindent
        this.aceEditor.commands.bindKey({ win: 'Shift-Tab', mac: 'Shift-Tab' }, (editor) => {
            editor.blockOutdent();
            return true; // Prevent default
        });
        
        // Sync ACE content with our state
        this.aceEditor.session.on('change', () => {
            if (this.isCodeMode) {
                this.updateHistory();
            }
        });
    },

    toggleMode() {
        this.isCodeMode = !this.isCodeMode;
        if (this.isCodeMode) {
            if (!this.aceEditor) {
                this.initAceEditor();
            }
            this.aceEditor.setValue(this.inputText, -1);
            setTimeout(() => this.aceEditor.focus(), 0);
        } else {
            this.inputText = this.aceEditor.getValue();
        }
        this.updateVisibility();
    },

    updateVisibility() {
        const textArea = document.getElementById('full-screen-input');
        const aceContainer = document.getElementById('ace-editor');
        if (this.isCodeMode) {
            textArea.style.display = 'none';
            aceContainer.style.display = 'block';
            if (this.aceEditor) {
                this.aceEditor.resize();
            }
        } else {
            textArea.style.display = 'block';
            aceContainer.style.display = 'none';
        }
    },

    updateHistory() {
        const currentText = this.isCodeMode ? this.aceEditor.getValue() : this.inputText;
        // Don't save if the text hasn't changed
        if (this.lastSavedState === currentText) return;
        
        this.undoStack.push(this.lastSavedState);
        if (this.undoStack.length > this.maxStackSize) {
            this.undoStack.shift();
        }
        this.redoStack = [];
        this.lastSavedState = currentText;
    },

    undo() {
        if (!this.canUndo) return;
        
        const currentText = this.isCodeMode ? this.aceEditor.getValue() : this.inputText;
        this.redoStack.push(currentText);
        const previousText = this.undoStack.pop();
        
        if (this.isCodeMode) {
            this.aceEditor.setValue(previousText, -1);
        } else {
            this.inputText = previousText;
        }
        this.lastSavedState = previousText;
    },

    redo() {
        if (!this.canRedo) return;
        
        const currentText = this.isCodeMode ? this.aceEditor.getValue() : this.inputText;
        this.undoStack.push(currentText);
        const nextText = this.redoStack.pop();
        
        if (this.isCodeMode) {
            this.aceEditor.setValue(nextText, -1);
        } else {
            this.inputText = nextText;
        }
        this.lastSavedState = nextText;
    },

    clearText() {
        const currentText = this.isCodeMode ? this.aceEditor.getValue() : this.inputText;
        if (currentText) {
            this.updateHistory();
            if (this.isCodeMode) {
                this.aceEditor.setValue('');
            } else {
                this.inputText = '';
            }
            this.lastSavedState = '';
        }
    },

    toggleWrap() {
        this.wordWrap = !this.wordWrap;
        if (this.isCodeMode && this.aceEditor) {
            this.aceEditor.setOption('wrap', this.wordWrap);
        }
    },

    async pasteFromClipboard() {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                // Save current state for undo
                this.updateHistory();
                
                // Update the appropriate editor
                if (this.isCodeMode && this.aceEditor) {
                    const currentPosition = this.aceEditor.getCursorPosition();
                    const currentContent = this.aceEditor.getValue();
                    const beforeCursor = currentContent.substring(0, this.aceEditor.session.doc.positionToIndex(currentPosition));
                    const afterCursor = currentContent.substring(this.aceEditor.session.doc.positionToIndex(currentPosition));
                    
                    // Insert text at cursor position
                    this.aceEditor.setValue(beforeCursor + text + afterCursor, -1);
                    
                    // Calculate new cursor position
                    const newPosition = this.aceEditor.session.doc.indexToPosition(beforeCursor.length + text.length);
                    this.aceEditor.moveCursorToPosition(newPosition);
                    this.aceEditor.focus();
                } else {
                    const textarea = document.getElementById('full-screen-input');
                    const start = textarea.selectionStart;
                    const end = textarea.selectionEnd;
                    
                    // Insert text at cursor position
                    this.inputText = this.inputText.substring(0, start) + text + this.inputText.substring(end);
                    
                    // Restore cursor position after the pasted text
                    setTimeout(() => {
                        textarea.selectionStart = textarea.selectionEnd = start + text.length;
                        textarea.focus();
                    }, 0);
                }
            }
        } catch (err) {
            console.error('Failed to read clipboard contents:', err);
        }
    },

    get canUndo() {
        return this.undoStack.length > 0;
    },

    get canRedo() {
        return this.redoStack.length > 0;
    }
};

// Register the full screen input modal with Alpine as a store
document.addEventListener('alpine:init', () => {
    Alpine.store('fullScreenInputModal', fullScreenInputModalProxy);
});

// Also register as a component for x-data usage
document.addEventListener('alpine:init', () => {
    Alpine.data('fullScreenInputModalProxy', () => fullScreenInputModalProxy);
});

const genericModalProxy = {
    isOpen: false,
    isLoading: false,
    title: '',
    description: '',
    html: '',

    async openModal(title, description, html, contentClasses = []) {
        const modalEl = document.getElementById('genericModal');
        const modalContent = document.getElementById('viewer');
        const modalAD = Alpine.$data(modalEl);

        modalAD.isOpen = true;
        modalAD.title = title
        modalAD.description = description
        modalAD.html = html

        modalContent.className = 'modal-content';
        modalContent.classList.add(...contentClasses);
    },

    handleClose() {
        this.isOpen = false;
    }
}

// Wait for Alpine to be ready
document.addEventListener('alpine:init', () => {
    Alpine.data('genericModalProxy', () => ({
        init() {
            Object.assign(this, genericModalProxy);
            // Ensure immediate file fetch when modal opens
            this.$watch('isOpen', async (value) => {
               // what now?
            });
        }
    }));
});

// Keep the global assignment for backward compatibility
window.genericModalProxy = genericModalProxy;