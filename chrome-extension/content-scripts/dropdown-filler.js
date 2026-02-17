/**
 * dropdown-filler.js
 * Universal dropdown/select handler for all types:
 * - Native <select> elements
 * - React-Select components
 * - ARIA comboboxes
 * - Custom dropdowns
 */

(function () {
    class DropdownFiller {
        /**
         * Detect the type of dropdown element
         * @param {HTMLElement} element - The element to analyze
         * @returns {string} Type: 'native', 'react-select', 'aria-combobox', or 'unknown'
         */
        static detectType(element) {
            if (!element) return 'unknown';

            // Native <select>
            if (element.tagName === 'SELECT') {
                return 'native';
            }

            // React-Select (check for common class patterns)
            const parent = element.closest('[class*="select"]') || element;
            const classList = parent.className || '';
            if (classList.includes('select') ||
                classList.includes('Select') ||
                element.querySelector('[class*="select"]')) {
                return 'react-select';
            }

            // ARIA combobox
            if (element.getAttribute('role') === 'combobox' ||
                element.getAttribute('aria-haspopup') === 'listbox') {
                return 'aria-combobox';
            }

            return 'unknown';
        }

        /**
         * Fill a native <select> element
         * @param {HTMLSelectElement} selectElement 
         * @param {string} value - The value to select
         * @returns {boolean} Success status
         */
        static fillNative(selectElement, value) {
            if (!selectElement || selectElement.tagName !== 'SELECT') {
                return false;
            }

            const options = Array.from(selectElement.options);
            let selectedOption = null;

            // Strategy 1: Exact value match
            selectedOption = options.find(opt =>
                opt.value.toLowerCase() === value.toLowerCase()
            );

            // Strategy 2: Exact text match
            if (!selectedOption) {
                selectedOption = options.find(opt =>
                    opt.text.toLowerCase() === value.toLowerCase()
                );
            }

            // Strategy 3: Partial text match (contains)
            if (!selectedOption) {
                selectedOption = options.find(opt =>
                    opt.text.toLowerCase().includes(value.toLowerCase())
                );
            }

            // Strategy 4: Value contains search term
            if (!selectedOption) {
                selectedOption = options.find(opt =>
                    value.toLowerCase().includes(opt.text.toLowerCase())
                );
            }

            if (selectedOption) {
                selectElement.value = selectedOption.value;

                // Trigger all necessary events
                selectElement.dispatchEvent(new Event('change', { bubbles: true }));
                selectElement.dispatchEvent(new Event('input', { bubbles: true }));
                selectElement.dispatchEvent(new Event('blur', { bubbles: true }));

                console.log(`✅ Native select filled: "${selectedOption.text}"`);
                return true;
            }

            console.warn(`⚠️ No matching option found for: "${value}"`);
            return false;
        }

        /**
         * Fill a React-Select component
         * @param {HTMLElement} container - The React-Select container
         * @param {string} value - The value to select
         * @returns {Promise<boolean>} Success status
         */
        static async fillReactSelect(container, value) {
            if (!container) return false;

            try {
                // Find the control element (what user clicks)
                const control = container.querySelector('[class*="control"]') ||
                    container.querySelector('[class*="Select"]') ||
                    container;

                // Click to open dropdown
                control.click();
                await this.sleep(500); // Wait for dropdown to open

                // Find the input field
                const input = container.querySelector('input[role="combobox"]') ||
                    container.querySelector('input');

                if (input) {
                    // Type the value (triggers filtering)
                    this.setNativeValue(input, value);
                    await this.sleep(300); // Wait for options to filter
                }

                // Find matching option in dropdown
                const options = document.querySelectorAll('[class*="option"]');
                for (let option of options) {
                    const text = option.textContent.toLowerCase();
                    const searchTerm = value.toLowerCase();

                    if (text.includes(searchTerm) || searchTerm.includes(text)) {
                        option.click();
                        console.log(`✅ React-Select filled: "${option.textContent}"`);
                        return true;
                    }
                }

                // No match found, close dropdown
                document.body.click();
                console.warn(`⚠️ No matching React-Select option for: "${value}"`);
                return false;

            } catch (error) {
                console.error('React-Select fill error:', error);
                return false;
            }
        }

        /**
         * Fill an ARIA combobox
         * @param {HTMLElement} element 
         * @param {string} value 
         * @returns {Promise<boolean>}
         */
        static async fillARIACombobox(element, value) {
            if (!element) return false;

            try {
                // Expand the combobox
                element.click();
                element.focus();
                await this.sleep(300);

                // Find the associated listbox
                const listboxId = element.getAttribute('aria-controls') ||
                    element.getAttribute('aria-owns');
                let listbox = listboxId ? document.getElementById(listboxId) : null;

                // Fallback: find any visible listbox
                if (!listbox) {
                    listbox = document.querySelector('[role="listbox"]:not([hidden])');
                }

                if (!listbox) {
                    console.warn('⚠️ Could not find listbox');
                    return false;
                }

                // Find matching option
                const options = listbox.querySelectorAll('[role="option"]');
                for (let option of options) {
                    const text = option.textContent.toLowerCase();
                    const searchTerm = value.toLowerCase();

                    if (text.includes(searchTerm) || searchTerm.includes(text)) {
                        option.click();
                        console.log(`✅ ARIA combobox filled: "${option.textContent}"`);
                        return true;
                    }
                }

                // Close combobox if no match
                element.blur();
                console.warn(`⚠️ No matching ARIA option for: "${value}"`);
                return false;

            } catch (error) {
                console.error('ARIA combobox fill error:', error);
                return false;
            }
        }

        /**
         * Universal fill method - detects type and fills accordingly
         * @param {HTMLElement} element 
         * @param {string} value 
         * @returns {Promise<boolean>}
         */
        static async fill(element, value) {
            if (!element || !value) {
                console.warn('⚠️ Missing element or value for dropdown fill');
                return false;
            }

            const type = this.detectType(element);
            console.log(`🔍 Detected dropdown type: ${type}`);

            switch (type) {
                case 'native':
                    return this.fillNative(element, value);

                case 'react-select':
                    const container = element.closest('[class*="select"]') || element;
                    return await this.fillReactSelect(container, value);

                case 'aria-combobox':
                    return await this.fillARIACombobox(element, value);

                default:
                    console.warn('⚠️ Unknown dropdown type, attempting native fill');
                    return this.fillNative(element, value);
            }
        }

        /**
         * Helper: Set native value (React-compatible)
         */
        static setNativeValue(element, value) {
            const valueSetter = Object.getOwnPropertyDescriptor(element, 'value')?.set;
            const prototype = Object.getPrototypeOf(element);
            const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;

            if (valueSetter && valueSetter !== prototypeValueSetter) {
                prototypeValueSetter.call(element, value);
            } else if (valueSetter) {
                valueSetter.call(element, value);
            }

            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }

        /**
         * Helper: Sleep/delay
         */
        static sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
    }

    // Export globally
    window.DropdownFiller = DropdownFiller;
    console.log('📋 DropdownFiller loaded');

})();
