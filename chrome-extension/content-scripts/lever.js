/**
 * lever.js
 * Auto-fill logic specifically for Lever ATS.
 */

(function () {
    // 1. Check Platform
    const platform = window.ATSDetector.getPlatform();
    if (platform !== 'lever' && !window.location.href.includes('lever.co')) return;

    console.log("🏢 Lever Handler Started");
    window.VisualFeedback.showToast("SmartJobApply: Detecting Lever Fields...", "info");

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

        // 1. Lever-specific ID/Name patterns
        for (const key of keywords) {
            // Lever often uses name="name", name="email", etc.
            field = document.querySelector(`input[name="${key}"]`) ||
                document.querySelector(`input[name*="${key}"]`);
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
                currentField = document.querySelector(`input[name="${field.name}"]`) || findField(keywords, 'input');
            }

            if (!currentField) {
                if (retries > 0) setTimeout(() => tryFill(retries - 1), 500);
                return;
            }

            if (currentField.value === value) {
                VF.markSafe(currentField);
                return;
            }

            console.log(`✏️ Lever: Filling ${keywords[0]} (Attempt ${6 - retries})`);
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
        const MAX_ATTEMPTS = 20;
        console.log(`⏳ Lever: Attempt ${attempt}/${MAX_ATTEMPTS} to find fields...`);

        // Check for main form
        const form = document.querySelector('form');
        const inputs = document.querySelectorAll('input');

        if ((!form || inputs.length < 2) && attempt < MAX_ATTEMPTS) {
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

        // Links (Lever often has specific "urls[LinkedIn]" names)
        if (fillField(Mappings.linkedin, Profile.linkedin)) filledCount++;
        if (fillField(Mappings.github, Profile.github)) filledCount++;
        if (fillField(Mappings.portfolio, Profile.portfolio)) filledCount++;

        // Resume
        const resumeBtn = document.querySelector('input[type="file"]');
        if (resumeBtn) {
            const target = resumeBtn.parentElement && resumeBtn.tagName === 'INPUT' ? resumeBtn.parentElement : resumeBtn;
            VF.markUnsafe(target, "Please upload your resume");
        }

        if (filledCount > 0) {
            VF.showToast(`✅ Auto-filled ${filledCount} fields!`, "success");
            console.log("🎉 Lever Auto-fill Complete");
        } else if (attempt < MAX_ATTEMPTS) {
            setTimeout(() => runAutoFill(attempt + 1), 500);
        } else {
            if (attempt === MAX_ATTEMPTS) console.warn("❌ Lever Auto-fill timed out.");
        }
    };

    runAutoFill();

    // Re-run on clicks (e.g., "Apply with Resume" might reveal fields)
    document.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
            setTimeout(() => runAutoFill(1), 1000);
        }
    });

})();
