/**
 * smartrecruiters.js
 * Auto-fill logic specifically for SmartRecruiters ATS.
 * Handles React SPA dynamic loading and data-test attributes.
 */

(function () {
    // 1. Check Platform
    const platform = window.ATSDetector.getPlatform();
    if (platform !== 'smartrecruiters' && !window.location.href.includes('smartrecruiters.com')) return;

    console.log("🏢 SmartRecruiters Handler Started");
    window.VisualFeedback.showToast("SmartJobApply: Detecting SmartRecruiters...", "info");

    const { Profile, Mappings } = window.SmartJobApply;
    const { findField } = window.FieldFinder;
    const VF = window.VisualFeedback;

    // 2. Define Filling Logic (Browser Native Simulation)
    const setNativeValue = (element, value) => {
        element.focus();
        element.value = '';
        const success = document.execCommand('insertText', false, value);

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
        let field = null;

        // 1. SmartRecruiters Specific Selectors (data-test > name > id)
        for (const key of keywords) {
            // SmartRecruiters uses data-test attributes heavily
            field = document.querySelector(`input[data-test="${key}"]`) ||
                document.querySelector(`input[name="${key}"]`) ||
                document.querySelector(`input[id*="${key}"]`);

            if (field) break;
        }

        // 2. Fallback
        if (!field) {
            field = findField(keywords, 'input');
        }

        if (!field) return false;

        // Persistent Fill Function
        const tryFill = (retries) => {
            let currentField = field;
            if (!document.contains(field)) {
                currentField = document.querySelector(`input[data-test="${field.getAttribute('data-test')}"]`) ||
                    findField(keywords, 'input');
            }

            if (!currentField) {
                if (retries > 0) setTimeout(() => tryFill(retries - 1), 500);
                return;
            }

            if (currentField.value === value) {
                VF.markSafe(currentField);
                return;
            }

            console.log(`✏️ SR: Filling ${keywords[0]} (Attempt ${6 - retries})`);
            setNativeValue(currentField, value);
            VF.markSafe(currentField);

            if (retries > 0) {
                setTimeout(() => tryFill(retries - 1), 500);
            }
        };

        tryFill(5);
        return true;
    };

    // 3. Execution Function
    const runAutoFill = (attempt = 1) => {
        const MAX_ATTEMPTS = 30; // Longer wait for SPA (15 sec)
        console.log(`⏳ SmartRecruiters: Attempt ${attempt}/${MAX_ATTEMPTS} to find form...`);

        // Check for specific SR form container or enough inputs
        const form = document.querySelector('st-application-form') || document.querySelector('form');
        const inputs = document.querySelectorAll('input');

        if ((!form && inputs.length < 3) && attempt < MAX_ATTEMPTS) {
            setTimeout(() => runAutoFill(attempt + 1), 500);
            return;
        }

        let filledCount = 0;

        // Basic Info
        if (fillField(Mappings.firstName, Profile.firstName)) filledCount++;
        if (fillField(Mappings.lastName, Profile.lastName)) filledCount++;
        if (fillField(Mappings.email, Profile.email)) filledCount++;
        if (fillField(Mappings.phone, Profile.phone)) filledCount++;

        // Links
        if (fillField(Mappings.linkedin, Profile.linkedin)) filledCount++;
        if (fillField(Mappings.github, Profile.github)) filledCount++;
        if (fillField(Mappings.portfolio, Profile.portfolio)) filledCount++;

        // Location (Common in SR)
        if (fillField(['city', 'location'], Profile.city + ", " + Profile.state)) filledCount++;

        // Resume (sr uses specific widget)
        const resumeBtn = document.querySelector('input[type="file"]') ||
            document.querySelector('button[aria-label="Upload resume"]');
        if (resumeBtn) {
            const target = resumeBtn.parentElement && resumeBtn.tagName === 'INPUT' ? resumeBtn.parentElement : resumeBtn;
            VF.markUnsafe(target, "Please upload your resume");
        }

        if (filledCount > 0) {
            VF.showToast(`✅ Auto-filled ${filledCount} fields!`, "success");
            console.log("🎉 SmartRecruiters Auto-fill Complete");
        } else if (attempt < MAX_ATTEMPTS) {
            setTimeout(() => runAutoFill(attempt + 1), 500);
        } else {
            // Only log warning, don't toast to avoid spam on non-apply pages
            console.warn("❌ SmartRecruiters Auto-fill timed out.");
        }
    };

    // Wait slightly longer for SR initial load
    setTimeout(() => runAutoFill(), 1000);

    // Re-run on clicks (SPA navigation)
    document.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
            setTimeout(() => runAutoFill(1), 1500);
        }
    });

})();
