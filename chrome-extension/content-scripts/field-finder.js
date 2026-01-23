/**
 * field-finder.js
 * Robust strategy for locating input fields using multiple heuristics.
 */

window.FieldFinder = {
    /**
     * Find an input element based on a list of potential keywords.
     * Strategies:
     * 1. Check <label> text content -> associated input
     * 2. Check input [placeholder]
     * 3. Check input [name]
     * 4. Check input [aria-label]
     * 
     * @param {string[]} keywords - List of terms to match (e.g., ['first name', 'fname'])
     * @param {string} type - 'input', 'select', 'textarea'
     */
    findField: function (keywords, type = 'input') {
        const lowerKeywords = keywords.map(k => k.toLowerCase());

        // Helper to check text match
        const matches = (text) => {
            if (!text) return false;
            const t = text.toLowerCase();
            return lowerKeywords.some(k => t.includes(k));
        };

        // Strategy 1: Explicit Labels
        // <label for="id">First Name</label>
        const labels = Array.from(document.querySelectorAll('label'));
        for (const label of labels) {
            if (matches(label.innerText)) {
                // Check 'for' attribute
                if (label.htmlFor) {
                    const el = document.getElementById(label.htmlFor);
                    if (el) return el;
                }
                // Check implicit nesting
                // <label>First Name <input /></label>
                const nested = label.querySelector(type);
                if (nested) return nested;
            }
        }

        // Strategy 2: Placeholder / Name / Aria
        // Get all candidate elements
        const elements = Array.from(document.querySelectorAll(type));

        for (const el of elements) {
            // Ignore hidden inputs
            const style = window.getComputedStyle(el);
            if (el.type === 'hidden' ||
                el.style.display === 'none' ||
                el.style.visibility === 'hidden' ||
                style.display === 'none' ||
                style.visibility === 'hidden') {
                continue;
            }
            const placeholder = el.getAttribute('placeholder');
            const name = el.getAttribute('name');
            const ariaLabel = el.getAttribute('aria-label');
            const id = el.id;

            if (matches(placeholder) ||
                matches(name) ||
                matches(ariaLabel) ||
                matches(id)) {
                return el;
            }
        }

        return null;
    }
};

console.log("🔍 SmartJobApply Field Finder Loaded");
