/**
 * greenhouse.js
 * Auto-fill logic specifically for Greenhouse ATS.
 */

(function () {
    // 1. Check Platform
    const platform = window.ATSDetector.getPlatform();
    if (platform !== 'greenhouse') return;

    console.log("🧩 Greenhouse Handler Started");
    window.VisualFeedback.showToast("SmartJobApply: Detecting Greenhouse Fields...", "info");

    const { Profile, Mappings } = window.SmartJobApply;
    const { findField } = window.FieldFinder;
    // Don't destructure VisualFeedback to preserve 'this' context
    const VF = window.VisualFeedback;

    // 2. Define Filling Logic (Nuclear Option)
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
        // DIRECT ID STRATEGY (Priority 1)
        // Based on user diagnostics: ids are "first_name", "last_name", "email", "phone"
        let field = null;

        // Map common keywords to specific Greenhouse IDs
        if (keywords.includes('first_name')) field = document.getElementById('first_name');
        else if (keywords.includes('last_name')) field = document.getElementById('last_name');
        else if (keywords.includes('email')) field = document.getElementById('email');
        else if (keywords.includes('phone')) field = document.getElementById('phone');

        // FALLBACK: Use Smart Finder (Priority 2)
        if (!field) {
            field = findField(keywords, 'input');
        }

        if (!field) return false;

        // Persistent Fill Function (Retries if value is wiped)
        const tryFill = (retries) => {
            // Re-find element in case DOM was trashed
            let currentField = document.getElementById(field.id); // Try ID again
            if (!currentField) currentField = findField(keywords, 'input'); // Fallback

            if (!currentField) {
                if (retries > 0) setTimeout(() => tryFill(retries - 1), 500);
                return;
            }

            if (currentField.value === value) {
                VF.markSafe(currentField);
                return; // Success
            }

            console.log(`✏️ Filling ${keywords[0]} (Attempt ${6 - retries}) on #${currentField.id}`);
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
    const runAutoFill = async (attempt = 1) => {
        const MAX_ATTEMPTS = 20; // 10 seconds total (20 * 500ms)
        console.log(`⏳ Greenhouse: Attempt ${attempt}/${MAX_ATTEMPTS} to find fields...`);

        // Check if main form exists
        const form = document.querySelector('form') || document.querySelector('#main_content');
        if (!form && attempt < MAX_ATTEMPTS) {
            setTimeout(() => runAutoFill(attempt + 1), 500);
            return;
        }

        let filledCount = 0;

        // Basic Info
        if (fillField(Mappings.firstName, Profile.firstName)) filledCount++;
        if (fillField(Mappings.lastName, Profile.lastName)) filledCount++;
        if (fillField(Mappings.email, Profile.email)) filledCount++;
        if (fillField(Mappings.phone, Profile.phone)) filledCount++;
        if (fillField(Mappings.linkedin, Profile.linkedin)) filledCount++;

        // Website/Portfolio (Optional)
        fillField(Mappings.portfolio, Profile.portfolio);
        fillField(Mappings.github, Profile.github);

        // Location Fields
        if (fillField(Mappings.city, Profile.city)) filledCount++;
        if (fillField(Mappings.state, Profile.state)) filledCount++;
        if (fillField(Mappings.zip, Profile.zip)) filledCount++;
        if (fillField(Mappings.location, Profile.location)) filledCount++;

        // Education
        fillField(Mappings.school, Profile.school);
        fillField(Mappings.degree, Profile.degree);
        fillField(Mappings.major, Profile.major);

        // Professional
        fillField(Mappings.yearsExperience, Profile.yearsExperience);
        fillField(Mappings.startDate, Profile.startDate);

        // DEMOGRAPHICS - Using DropdownFiller
        const DF = window.DropdownFiller;

        // Gender
        const genderField = findField(Mappings.gender, 'select') ||
            findField(Mappings.gender, 'input');
        if (genderField) {
            if (await DF.fill(genderField, Profile.gender)) {
                filledCount++;
                VF.markSafe(genderField);
            }
        }

        // Race
        const raceField = findField(Mappings.race, 'select') ||
            findField(Mappings.race, 'input');
        if (raceField) {
            if (await DF.fill(raceField, Profile.race)) {
                filledCount++;
                VF.markSafe(raceField);
            }
        }

        // Ethnicity (Hispanic/Latino)
        const ethnicityField = findField(Mappings.ethnicity, 'select') ||
            findField(Mappings.ethnicity, 'input');
        if (ethnicityField) {
            if (await DF.fill(ethnicityField, Profile.ethnicity)) {
                filledCount++;
                VF.markSafe(ethnicityField);
            }
        }

        // Veteran Status
        const veteranField = findField(Mappings.veteran, 'select') ||
            findField(Mappings.veteran, 'input');
        if (veteranField) {
            if (await DF.fill(veteranField, Profile.veteran)) {
                filledCount++;
                VF.markSafe(veteranField);
            }
        }

        // Disability Status
        const disabilityField = findField(Mappings.disability, 'select') ||
            findField(Mappings.disability, 'input');
        if (disabilityField) {
            if (await DF.fill(disabilityField, Profile.disability)) {
                filledCount++;
                VF.markSafe(disabilityField);
            }
        }

        // Work Authorization
        const workAuthField = findField(Mappings.workAuthorization, 'select') ||
            findField(Mappings.workAuthorization, 'input');
        if (workAuthField) {
            if (await DF.fill(workAuthField, Profile.workAuthorization)) {
                filledCount++;
                VF.markSafe(workAuthField);
            }
        }

        // Sponsorship
        const sponsorshipField = findField(Mappings.sponsorship, 'select') ||
            findField(Mappings.sponsorship, 'input');
        if (sponsorshipField) {
            if (await DF.fill(sponsorshipField, Profile.sponsorship)) {
                filledCount++;
                VF.markSafe(sponsorshipField);
            }
        }

        // Resume Section (Always check)
        const resumeBtn = document.querySelector('button[aria-label="Upload Resume"]') ||
            document.querySelector('[data-source="attach"]') ||
            document.querySelector('input[type="file"]');

        if (resumeBtn) {
            // Handle both button and input cases
            const target = resumeBtn.parentElement && resumeBtn.tagName === 'INPUT' ? resumeBtn.parentElement : resumeBtn;
            VF.markUnsafe(target, "Please upload your resume");
        }

        // Decision: Stop or Retry?
        if (filledCount > 0) {
            VF.showToast(`✅ Auto-filled ${filledCount} fields!`, "success");
            console.log("🎉 Greenhouse Auto-fill Complete");
        } else if (attempt < MAX_ATTEMPTS) {
            // Continue polling if nothing found yet
            setTimeout(() => runAutoFill(attempt + 1), 500);
        } else {
            VF.showToast("⚠️ Could not find fields. Trying manual mode.", "warning");
            console.warn("❌ Greenhouse Auto-fill timed out.");
        }
    };

    // 4. Start Polling
    runAutoFill();

    // Optional: Re-run on clicks
    document.addEventListener('click', (e) => {
        // Only re-run if clicking something that might change the form (like "Apply with LinkedIn")
        if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
            setTimeout(() => runAutoFill(1), 1000);
        }
    });

})();
