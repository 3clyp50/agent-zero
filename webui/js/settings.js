const settingsModalProxy = {
    isOpen: false,
    settings: {},
    resolvePromise: null,

    async openModal() {
        const modalEl = document.getElementById('settingsModal');
        const modalAD = Alpine.$data(modalEl);

        // Get settings from backend
        try {
            const response = await fetch('/settings_get');
            const data = await response.json();

            const settings = {
                "title": "Settings",
                "buttons": [
                    {
                        id: "export",
                        title: "Export Settings",
                        classes: "btn btn-secondary"
                    },
                    {
                        id: "import",
                        title: "Import Settings",
                        classes: "btn btn-secondary"
                    },
                    {
                        id: "cancel",
                        title: "Cancel",
                        classes: "btn btn-cancel"
                    },
                    {
                        id: "save",
                        title: "Save",
                        classes: "btn btn-ok"
                    },
                ],
                sections: data.settings.sections
            };

            modalAD.isOpen = true; // Open the modal
            modalAD.settings = settings; // Populate settings

            return new Promise(resolve => {
                this.resolvePromise = resolve;
            });

        } catch (e) {
            window.toastFetchError("Error getting settings", e);
        }
    },

    async handleButton(buttonId) {
        if (buttonId === 'save') {
            const modalEl = document.getElementById('settingsModal');
            const modalAD = Alpine.$data(modalEl);
            try {
                const resp = await window.sendJsonData("/settings_set", modalAD.settings);
                document.dispatchEvent(new CustomEvent('settings-updated', { detail: resp.settings }));
                if (this.resolvePromise) {
                    this.resolvePromise({
                        status: 'saved',
                        data: resp.settings
                    });
                    this.resolvePromise = null;
                }
                modalAD.isOpen = false; // Close the modal
            } catch (e) {
                window.toastFetchError("Error saving settings", e);
                return;
            }
        } else if (buttonId === 'cancel') {
            this.handleCancel();
        } else if (buttonId === 'export') {
            this.exportSettings();
        } else if (buttonId === 'import') {
            this.importSettings();
        }
    },

    async handleCancel() {
        if (this.resolvePromise) {
            this.resolvePromise({
                status: 'cancelled',
                data: null
            });
            this.resolvePromise = null;
        }
        // Update the modal's isOpen state
        const modalEl = document.getElementById('settingsModal');
        const modalAD = Alpine.$data(modalEl);
        modalAD.isOpen = false;
    },

    handleFieldButton(field) {
        console.log(`Button clicked: ${field.action}`);
    },

    exportSettings() {

        const values = {};

        // Iterate through each section to extract values
        this.settings.sections.forEach((section, sectionIndex) => {
            // Use section.title as the key
            const sectionKey = section.title;

            if (!sectionKey) {
                console.warn(`Section at index ${sectionIndex} lacks a title. Skipping.`);
                return; // Skip sections without a title
            }

            values[sectionKey] = {};

            // Ensure the section has fields
            if (Array.isArray(section.fields)) {
                section.fields.forEach((field, fieldIndex) => {
                    // Use field.id as the key
                    const fieldKey = field.id;

                    if (!fieldKey) {
                        console.warn(`Field at index ${fieldIndex} in section "${sectionKey}" lacks an id. Skipping.`);
                        return; // Skip fields without an id
                    }

                    values[sectionKey][fieldKey] = field.value;
                });
            } else {
                console.warn(`Section "${sectionKey}" does not have a 'fields' array.`);
            }
        });

        // Create and download the JSON file
        const settingsBlob = new Blob([JSON.stringify(values, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(settingsBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'settings.json'; // Filename indicates it's only values
        a.click();
        URL.revokeObjectURL(url);
    },

    importSettings() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = () => {
                    try {
                        const importedValues = JSON.parse(reader.result);
                        const currentSettings = this.settings.sections;

                        // Track import results
                        let importedSections = 0;
                        let skippedSections = 0;
                        let importedFields = 0;
                        let skippedFields = 0;

                        // Iterate through each section in the imported data
                        for (const sectionKey in importedValues) {
                            // Find the section by title
                            const section = currentSettings.find(sec => sec.title === sectionKey);

                            if (section) {
                                importedSections++;
                                // Iterate through each field in the section
                                for (const fieldKey in importedValues[sectionKey]) {
                                    // Find the field by id
                                    const field = section.fields.find(f => f.id === fieldKey);

                                    if (field) {
                                        field.value = importedValues[sectionKey][fieldKey];
                                        importedFields++;
                                    } else {
                                        console.warn(`Field "${fieldKey}" not found in section "${sectionKey}". Skipping.`);
                                        skippedFields++;
                                    }
                                }
                            } else {
                                console.warn(`Section "${sectionKey}" not found in current settings. Skipping.`);
                                skippedSections++;
                            }
                        }

                        window.toastMessage("Settings imported successfully!");
                    } catch (error) {
                        window.toastFetchError("Error importing settings", error);
                    }
                };
                reader.readAsText(file);
            }
        });
        input.click();
    },

    // ... (other methods, if any)
};


// function initSettingsModal() {

//     window.openSettings = function () {
//         proxy.openModal().then(result => {
//             console.log(result);  // This will log the result when the modal is closed
//         });
//     }

//     return proxy
// }


// document.addEventListener('alpine:init', () => {
//     Alpine.store('settingsModal', initSettingsModal());
// });
