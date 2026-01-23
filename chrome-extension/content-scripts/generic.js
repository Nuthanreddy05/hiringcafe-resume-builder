/**
 * generic.js
 * Catch-all auto-fill logic for unsupported ATS and generic forms.
 * Relies heavily on FieldFinder heuristics.
 */

(function () {
    // 1. Check Platform
    const platform = window.ATSDetector.getPlatform();
    // Only run if NO specific platform is detected
    if (platform !== 'unknown' && platform !== 'generic') return;

    // Additional check: Don't run on non-job sites (basic heuristic)
    const pageText = document.body.innerText.toLowerCase();
    const likelyJobSite =
        window.location.href.includes('career') ||
        window.location.href.includes('job') ||
        window.location.href.includes('apply') ||
        pageText.includes('resume') ||
        pageText.includes('cv') ||
        pageText.includes('application');

    if (!likelyJobSite) return;

    console.log("🌍 Generic Handler Started");

    // Only show toast if we actually find fields to fill, to avoid spamming every site
    // window.VisualFeedback.showToast("SmartJobApply: Checking Generic Form...", "info");

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
        // PURE HEURISTIC STRATEGY
        const field = findField(keywords, 'input') || findField(keywords, 'select');

        if (!field) return false;

        // Persistent Fill Function
        const tryFill = (retries) => {
            let currentField = field;
            if (!document.contains(field)) {
                currentField = findField(keywords, 'input');
            }

            if (!currentField) {
                if (retries > 0) setTimeout(() => tryFill(retries - 1), 500);
                return;
            }

            if (currentField.value === value) {
                VF.markSafe(currentField);
                return;
            }

            console.log(`✏️ Generic: Filling ${keywords[0]} (Attempt ${6 - retries})`);
            setNativeValue(currentField, value);
            VF.markSafe(currentField);

            if (retries > 0) {
                setTimeout(() => tryFill(retries - 1), 500);
            }
        };

        tryFill(3); // Fewer retries for generic to be less aggressive
        return true;
    };

    // 3. Execution Function
    const runAutoFill = (attempt = 1) => {
        const MAX_ATTEMPTS = 10; // Shorter wait for generic
        // console.log(`⏳ Generic: Attempt ${attempt}/${MAX_ATTEMPTS}...`);

        const inputs = document.querySelectorAll('input');
        if (inputs.length < 2 && attempt < MAX_ATTEMPTS) {
            setTimeout(() => runAutoFill(attempt + 1), 500);
            return;
        }

        let filledCount = 0;

        // Basic Info
        if (fillField(Mappings.fullName, Profile.fullName)) filledCount++;
        // Sometimes valid split names
        if (fillField(Mappings.firstName, Profile.firstName)) filledCount++;
        if (fillField(Mappings.lastName, Profile.lastName)) filledCount++;

        if (fillField(Mappings.email, Profile.email)) filledCount++;
        if (fillField(Mappings.phone, Profile.phone)) filledCount++;

        // Location
        if (fillField(['city', 'location'], Profile.city)) filledCount++;
        if (fillField(['zip', 'postal'], Profile.zip)) filledCount++;

        // Links
        if (fillField(Mappings.linkedin, Profile.linkedin)) filledCount++;
        if (fillField(Mappings.github, Profile.github)) filledCount++;
        if (fillField(Mappings.portfolio, Profile.portfolio)) filledCount++;

        // Resume (Generic)
        const resumeInput = document.querySelector('input[type="file"]');
        if (resumeInput) {
            // Check if label contains "resume" or "cv"
            const label = resumeInput.labels?.[0]?.innerText?.toLowerCase() || '';
            const name = resumeInput.name.toLowerCase();
            if (name.includes('resume') || name.includes('cv') || label.includes('resume') || label.includes('cv')) {
                VF.markUnsafe(resumeInput.parentElement || resumeInput, "Please upload your resume");
            }
        }

        if (filledCount > 0) {
            VF.showToast(`✅ Generic Auto-fill: ${filledCount} fields`, "success");
            console.log("🎉 Generic Auto-fill Complete");
        } else if (attempt < MAX_ATTEMPTS) {
            setTimeout(() => runAutoFill(attempt + 1), 1000);
        }
    };

    // Run late to let other handlers finish first
    setTimeout(() => runAutoFill(), 1000);

})();
