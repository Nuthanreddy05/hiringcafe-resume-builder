/**
 * taleo.js
 * Auto-fill logic specifically for Taleo ATS.
 * Handles iframes and login walls.
 */

(function () {
    // 1. Check Platform
    const platform = window.ATSDetector.getPlatform();
    // Taleo often runs in iframes, so we check even if main platform isn't detected yet
    if (platform !== 'taleo' && !window.location.href.includes('taleo.net')) return;

    console.log("🏢 Taleo Handler Started", window.location.href);

    const { Profile, Mappings } = window.SmartJobApply || {};
    // Retry if global object not ready (common in iframes)
    if (!Profile) {
        setTimeout(() => window.location.reload(), 1000);
        return;
    }

    const { findField } = window.FieldFinder;
    // Don't destructure VisualFeedback to preserve 'this' context
    const VF = window.VisualFeedback;

    // 2. Define Filling Logic (Browser Native Simulation)
    const setNativeValue = (element, value) => {
        // Clear field first
        element.focus();
        element.value = '';

        // Simulating Human Typing via Browser Command
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

    // 3. Login Wall Detection
    const detectLoginWall = () => {
        const loginKeywords = [
            'sign in', 'log in', 'login',
            'create account', 'register',
            'returning candidate', 'new candidate'
        ];

        // Check page title and buttons
        const textContent = document.body.innerText.toLowerCase();
        const hasLoginText = loginKeywords.some(keyword => textContent.includes(keyword));
        const hasInputs = document.querySelectorAll('input[type="text"]').length > 3; // Forms usually have many inputs

        // If it looks like a login page (few inputs, login text)
        if (hasLoginText && !hasInputs) {
            console.warn('🚪 Taleo: Possible Login wall detected');
            VF.showToast("⚠️ Please Log In to Taleo first.", "warning");
            return true;
        }
        return false;
    };

    const fillField = (keywords, value) => {
        // STRATEGY: Hybrid (ID > Name > Smart Finder)
        let field = null;

        // 1. Try Specific IDs/Names common in Taleo
        for (const key of keywords) {
            field = document.querySelector(`input[id*="${key}"]`) ||
                document.querySelector(`input[name*="${key}"]`) ||
                document.querySelector(`input[id*="${key.toLowerCase()}"]`) ||
                document.querySelector(`input[name*="${key.toLowerCase()}"]`);
            if (field) break;
        }

        // 2. Fallback to Smart Finder if no direct match
        if (!field) {
            field = findField(keywords, 'input');
        }

        if (!field) return false;

        // Persistent Fill Function
        const tryFill = (retries) => {
            let currentField = field;
            if (!document.contains(field)) {
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

            console.log(`✏️ Taleo: Filling ${keywords[0]} (Attempt ${6 - retries})`);
            setNativeValue(currentField, value);
            VF.markSafe(currentField);

            if (retries > 0) {
                setTimeout(() => tryFill(retries - 1), 500);
            }
        };

        tryFill(5);
        return true;
    };

    // 4. Execution Function (Stateful)
    const runAutoFill = (attempt = 1) => {
        // If login wall, stop
        if (detectLoginWall() && attempt === 1) return;

        const MAX_ATTEMPTS = 20;
        console.log(`⏳ Taleo: Attempt ${attempt}/${MAX_ATTEMPTS} to find fields...`);

        // Taleo often uses iframes, verify we are in the right context
        const inputs = document.querySelectorAll('input');
        if (inputs.length < 2 && attempt < MAX_ATTEMPTS) {
            setTimeout(() => runAutoFill(attempt + 1), 500);
            return;
        }

        let filledCount = 0;

        // Basic Info
        if (fillField(Mappings.fullName, Profile.fullName)) filledCount++;
        if (fillField(Mappings.firstName, Profile.firstName)) filledCount++;
        if (fillField(Mappings.lastName, Profile.lastName)) filledCount++;
        if (fillField(Mappings.email, Profile.email)) filledCount++;
        if (fillField(Mappings.phone, Profile.phone)) filledCount++;

        // Links
        if (fillField(Mappings.linkedin, Profile.linkedin)) filledCount++;
        if (fillField(Mappings.github, Profile.github)) filledCount++;
        if (fillField(Mappings.portfolio, Profile.portfolio)) filledCount++;

        // Resume Section
        const resumeBtn = document.querySelector('input[type="file"]');
        if (resumeBtn) {
            const target = resumeBtn.parentElement && resumeBtn.tagName === 'INPUT' ? resumeBtn.parentElement : resumeBtn;
            VF.markUnsafe(target, "Please upload your resume");
        }

        // Decision: Stop or Retry?
        if (filledCount > 0) {
            VF.showToast(`✅ Auto-filled ${filledCount} fields!`, "success");
            console.log("🎉 Taleo Auto-fill Complete");
        } else if (attempt < MAX_ATTEMPTS) {
            setTimeout(() => runAutoFill(attempt + 1), 500);
        } else {
            // Only warn on last attempt
            if (attempt === MAX_ATTEMPTS) {
                console.warn("❌ Taleo Auto-fill timed out.");
            }
        }
    };

    // 5. Start Polling
    window.VisualFeedback.showToast("SmartJobApply: Checking Taleo...", "info");
    runAutoFill();

    // Re-run on clicks (Taleo has next buttons)
    document.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON' || e.target.type === 'submit' || e.target.closest('a')) {
            setTimeout(() => runAutoFill(1), 2000); // Longer wait for Taleo page loads
        }
    });

})();
