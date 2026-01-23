/**
 * visual-feedback.js
 * Handles visual cues for the user (Green/Yellow borders, Toasts).
 */

window.VisualFeedback = {
    // Styles
    styles: {
        safe: '2px solid #22c55e !important',   // Green-500
        unsafe: '2px solid #eab308 !important', // Yellow-500
        error: '2px solid #ef4444 !important'   // Red-500
    },

    /**
     * Mark a field as safely auto-filled.
     * @param {HTMLElement} element 
     */
    markSafe: function (element) {
        if (!element) return;
        element.style.cssText += `border: ${this.styles.safe};`;
        // Remove previous cues
        element.classList.remove('sja-unsafe');
        element.classList.add('sja-safe');
    },

    /**
     * Mark a field as requiring manual attention.
     * @param {HTMLElement} element 
     * @param {string} reason - Optional reasoning
     */
    markUnsafe: function (element, reason) {
        if (!element) return;
        element.style.cssText += `border: ${this.styles.unsafe};`;
        element.title = reason || "Please review this field";
        element.classList.remove('sja-safe');
        element.classList.add('sja-unsafe');
    },

    /**
     * Show a temporary toast message at the top of the page.
     * @param {string} message 
     * @param {string} type - 'info', 'success', 'warning'
     */
    showToast: function (message, type = 'info') {
        let toast = document.getElementById('sja-toast');

        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'sja-toast';
            Object.assign(toast.style, {
                position: 'fixed',
                top: '20px',
                right: '20px',
                padding: '12px 24px',
                borderRadius: '8px',
                color: 'white',
                fontFamily: 'system-ui, sans-serif',
                fontSize: '14px',
                zIndex: '2147483647',
                boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                transition: 'opacity 0.3s ease'
            });
            document.body.appendChild(toast);
        }

        // Color based on type
        if (type === 'success') toast.style.backgroundColor = '#22c55e';
        else if (type === 'warning') toast.style.backgroundColor = '#eab308';
        else toast.style.backgroundColor = '#3b82f6'; // blue

        toast.textContent = message;
        toast.style.opacity = '1';

        // Auto-hide
        setTimeout(() => {
            toast.style.opacity = '0';
        }, 3000);
    },

    injectStyles: function () {
        // Optional: Inject a style tag if we need pseudo-elements or specific class behaviors
        const style = document.createElement('style');
        style.textContent = `
            .sja-safe { background-color: rgba(34, 197, 94, 0.05) !important; }
            .sja-unsafe { background-color: rgba(234, 179, 8, 0.05) !important; }
        `;
        document.head.appendChild(style);
    }
};

// Initialize styles
if (document.head) window.VisualFeedback.injectStyles();

console.log("🎨 SmartJobApply Visual Feedback Loaded");
