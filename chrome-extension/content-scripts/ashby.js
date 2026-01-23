/**
 * ashby.js
 * Auto-fill logic specifically for Ashby ATS.
 */

(function () {
    // 1. Check Platform
    const platform = window.ATSDetector.getPlatform();
    if (platform !== 'ashby') return;

    console.log("🏢 Ashby Handler Started");
    window.VisualFeedback.showToast("SmartJobApply: Detecting Ashby Fields...", "info");

    const { Profile, Mappings } = window.SmartJobApply;
    const { findField } = window.FieldFinder;
    // Don't destructure VisualFeedback to preserve 'this' context
    const VF = window.VisualFeedback;

    // 2. Define Filling Logic (Browser Native Simulation)
    const setNativeValue = (element, value) => {
        // Clear field first
        element.focus();
        element.value = '';

        // Simulating Human Typing via Browser Command (Best for React)
        const success = document.execCommand('insertText', false, value);

        // Fallback if execCommand fails
        if (!success || element.value !== value) {
            const valueSetter = Object.getOwnPropertyDescriptor(element, 'value').set;
            const prototype = Object.getPrototypeOf(element);
            const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;

            if (valueSetter && valueSetter !== prototypeValueSetter) {
                prototypeValueSetter.call(element, value);
            } else {
                valueSetter.call(element, value);
            }
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }

        element.dispatchEvent(new Event('blur', { bubbles: true }));
    };

    const fillField = (keywords, value) => {
        // STRATEGY: Hybrid (ID > Name > Smart Finder)
        let field = null;

        // 1. Try Specific IDs/Names common in Ashby
        // Ashby often uses specific IDs like 'name', 'email', 'phone-number'
        // We iterate through keywords to find exact matches first
        for (const key of keywords) {
            field = document.getElementById(key) ||
                document.querySelector(`input[name="${key}"]`) ||
                document.querySelector(`input[name*="${key}"]`);
            if (field) break;
        }

        // 2. Fallback to Smart Finder if no direct match
        if (!field) {
            field = findField(keywords, 'input');
        }

        if (!field) return false;

        // Persistent Fill Function (Retries if value is wiped)
        const tryFill = (retries) => {
            // Re-find element in case DOM was trashed
            let currentField = field;
            if (!document.contains(field)) {
                // Try to re-query if element is gone
                currentField = document.getElementById(field.id) || findField(keywords, 'input');
            }

            if (!currentField) {
                if (retries > 0) setTimeout(() => tryFill(retries - 1), 500);
                return;
            }

            if (currentField.value === value) {
                VF.markSafe(currentField);
                return; // Success
            }

            console.log(`✏️ Ashby: Filling ${keywords[0]} (Attempt ${6 - retries})`);
            setNativeValue(currentField, value);
            VF.markSafe(currentField);

            if (retries > 0) {
                setTimeout(() => tryFill(retries - 1), 500);
            }
        };

        tryFill(5); // Retry 5 times over ~2.5 seconds
        return true;
    };

    // 3. Execution Function (Stateful)
    const runAutoFill = (attempt = 1) => {
        const MAX_ATTEMPTS = 20; // 10 seconds total
        console.log(`⏳ Ashby: Attempt ${attempt}/${MAX_ATTEMPTS} to find fields...`);

        // Check if main form exists (Ashby forms vary, often just <body> or specific div)
        const form = document.querySelector('form') || document.querySelector('.ashby-application-form');

        // If no inputs found yet, keep waiting
        const inputs = document.querySelectorAll('input');
        if (inputs.length === 0 && attempt < MAX_ATTEMPTS) {
            setTimeout(() => runAutoFill(attempt + 1), 500);
            return;
        }

        let filledCount = 0;

        // Basic Info
        if (fillField(Mappings.fullName, Profile.fullName)) filledCount++;
        // Sometimes name is split
        if (fillField(Mappings.firstName, Profile.firstName)) filledCount++;
        if (fillField(Mappings.lastName, Profile.lastName)) filledCount++;

        if (fillField(Mappings.email, Profile.email)) filledCount++;
        if (fillField(Mappings.phone, Profile.phone)) filledCount++;

        // Links
        if (fillField(Mappings.linkedin, Profile.linkedin)) filledCount++;
        if (fillField(Mappings.github, Profile.github)) filledCount++;
        if (fillField(Mappings.portfolio, Profile.portfolio)) filledCount++;

        // Resume Section
        const resumeBtn = document.querySelector('button[aria-label="Upload Resume"]') ||
            document.querySelector('input[type="file"][name*="resume"]');

        if (resumeBtn) {
            const target = resumeBtn.parentElement && resumeBtn.tagName === 'INPUT' ? resumeBtn.parentElement : resumeBtn;
            VF.markUnsafe(target, "Please upload your resume");
        }

        // Decision: Stop or Retry?
        if (filledCount > 0) {
            VF.showToast(`✅ Auto-filled ${filledCount} fields!`, "success");
            console.log("🎉 Ashby Auto-fill Complete");
        } else if (attempt < MAX_ATTEMPTS) {
            setTimeout(() => runAutoFill(attempt + 1), 500);
        } else {
            VF.showToast("⚠️ Could not find fields. Trying manual mode.", "warning");
            console.warn("❌ Ashby Auto-fill timed out.");
        }
    };

    // 4. Start Polling
    runAutoFill();

    // Re-run on clicks (dynamic navigation)
    document.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
            setTimeout(() => runAutoFill(1), 1000);
        }
    });

})();
