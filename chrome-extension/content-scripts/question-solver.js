/**
 * Question Solver - AI Powered
 * Adds "✨ AI Answer" button to textareas
 */

(function () {
    window.QuestionSolver = window.QuestionSolver || {};

    const QS = window.QuestionSolver;
    QS.processing = false;

    // --- 1. Find and Enhance Fields ---
    QS.findTextAreas = () => {
        const textareas = document.querySelectorAll('textarea');
        textareas.forEach(textarea => {
            // Skip if already processed or too small (likely not a Q&A field)
            if (textarea.dataset.aiEnhanced || textarea.offsetHeight < 40) return;

            QS.injectButton(textarea);
            textarea.dataset.aiEnhanced = "true";
        });
    };

    // --- 2. Inject Button ---
    QS.injectButton = (textarea) => {
        const btn = document.createElement('button');
        btn.innerText = "✨ AI Answer";
        btn.className = "ai-solve-btn";

        // Style the button
        Object.assign(btn.style, {
            position: 'absolute',
            right: '10px',
            bottom: '10px',
            zIndex: '1000',
            backgroundColor: '#10b981', // Emerald 500
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '12px',
            cursor: 'pointer',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
            transition: 'all 0.2s',
            opacity: '0.8'
        });

        // Hover effect
        btn.onmouseover = () => btn.style.opacity = '1';
        btn.onmouseout = () => btn.style.opacity = '0.8';

        // Wrapper to position button relative to textarea
        const wrapper = document.createElement('div');
        Object.assign(wrapper.style, {
            position: 'relative',
            display: 'inline-block',
            width: textarea.style.width || '100%'
        });

        textarea.parentNode.insertBefore(wrapper, textarea);
        wrapper.appendChild(textarea);
        wrapper.appendChild(btn);

        // Click Handler
        btn.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            QS.solveQuestion(textarea, btn);
        };
    };

    // --- 3. Solve Logic ---
    QS.solveQuestion = async (textarea, btn) => {
        if (QS.processing) return;
        QS.processing = true;

        const originalText = btn.innerText;
        btn.innerText = "🤖 Thinking...";
        btn.style.backgroundColor = '#6366f1';

        const question = QS.getLabel(textarea) || textarea.placeholder || "";
        const isCoverLetter = /cover\s*letter|additional\s*info|supporting\s*doc/i.test(question);

        const context = {
            jobTitle: document.title,
            company: document.domain,
            url: window.location.href
        };

        try {
            chrome.runtime.sendMessage({
                action: isCoverLetter ? "generate_cover_letter" : "generate_answer",
                question: question,
                context: context
            }, (response) => {
                QS.processing = false;
                btn.innerText = originalText;
                btn.style.backgroundColor = '#10b981';

                if (response && response.answer) {
                    // Show Review Modal instead of auto-typing
                    QS.showReviewModal(textarea, question, response.answer, isCoverLetter);
                } else {
                    alert(`AI Error: ${response?.error || 'Unknown error'}`);
                }
            });
        } catch (e) {
            console.error(e);
            QS.processing = false;
            btn.innerText = "❌ Error";
        }
    };

    // --- 4. Review Modal ---
    QS.showReviewModal = (textarea, question, answer, isCoverLetter = false) => {
        // Remove existing
        const existing = document.getElementById('ai-review-modal');
        if (existing) existing.remove();

        // Create Modal Overlay
        const overlay = document.createElement('div');
        overlay.id = 'ai-review-modal';
        Object.assign(overlay.style, {
            position: 'fixed', top: '0', left: '0', right: '0', bottom: '0',
            backgroundColor: 'rgba(0,0,0,0.6)',
            zIndex: '100000',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: 'Inter, system-ui, sans-serif'
        });

        // Modal Content
        const modal = document.createElement('div');
        Object.assign(modal.style, {
            backgroundColor: 'white',
            borderRadius: '12px',
            width: isCoverLetter ? '800px' : '600px', // Wider for Cover Letter
            maxWidth: '90%',
            padding: '24px',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
            display: 'flex', flexDirection: 'column', gap: '16px'
        });

        // Header
        const header = document.createElement('div');
        header.innerHTML = `
            <h3 style="margin:0; font-size:18px; color:#111827;">${isCoverLetter ? '📄 AI Cover Letter' : '✨ AI Generated Answer'}</h3>
            <p style="margin:4px 0 0; font-size:13px; color:#6b7280;">${isCoverLetter ? 'Draft based on your resume and job title.' : 'Generic or specific based on your resume.'}</p>
        `;

        // Question Preview
        const qBox = document.createElement('div');
        qBox.style.cssText = "background:#f3f4f6; padding:12px; border-radius:8px; font-size:14px; color:#374151; font-style:italic;";
        qBox.innerText = question.length > 150 ? question.substring(0, 150) + "..." : question;

        // Answer Editor
        const editor = document.createElement('textarea');
        editor.value = answer;
        Object.assign(editor.style, {
            width: '100%', height: '150px',
            padding: '12px',
            borderRadius: '8px',
            border: '1px solid #d1d5db',
            fontSize: '14px',
            lineHeight: '1.5',
            resize: 'vertical',
            fontFamily: 'inherit'
        });

        // Footer Actions
        const actions = document.createElement('div');
        Object.assign(actions.style, {
            display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '8px'
        });

        const createBtn = (text, bg, onClick) => {
            const b = document.createElement('button');
            b.innerText = text;
            Object.assign(b.style, {
                padding: '8px 16px', borderRadius: '6px', border: 'none',
                backgroundColor: bg, color: 'white', cursor: 'pointer', fontWeight: '500'
            });
            b.onclick = onClick;
            return b;
        };

        const cancelBtn = createBtn("Cancel", "#6b7280", () => overlay.remove());
        const confirmBtn = createBtn("✅ Insert Answer", "#10b981", () => {
            QS.typeAnswer(textarea, editor.value);
            overlay.remove();
        });

        actions.appendChild(cancelBtn);
        actions.appendChild(confirmBtn);

        modal.appendChild(header);
        modal.appendChild(qBox);
        modal.appendChild(editor);
        modal.appendChild(actions);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
    };

    // --- 5. Helper: Get Label ---
    QS.getLabel = (element) => {
        if (element.id) {
            const label = document.querySelector(`label[for="${element.id}"]`);
            if (label) return label.innerText;
        }
        const parentLabel = element.closest('label');
        if (parentLabel) return parentLabel.innerText.replace(element.value, '');

        // 3. Preceding Text
        const prev = element.previousElementSibling;
        if (prev && (prev.tagName === 'LABEL' || prev.tagName === 'DIV' || prev.tagName === 'SPAN')) {
            return prev.innerText;
        }
        return "";
    };

    // --- 6. Human-Like Typing ---
    QS.typeAnswer = async (element, text) => {
        element.focus();
        element.value = "";

        for (let i = 0; i < text.length; i++) {
            element.value += text[i];
            element.scrollTop = element.scrollHeight;
            if (i % 5 === 0) await new Promise(r => setTimeout(r, Math.random() * 15 + 5));
        }

        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
    };

    // --- 7. Init ---
    const observer = new MutationObserver((mutations) => {
        QS.findTextAreas();
    });

    observer.observe(document.body, { childList: true, subtree: true });

    setTimeout(QS.findTextAreas, 1000);
    setTimeout(QS.findTextAreas, 3000);

})();
