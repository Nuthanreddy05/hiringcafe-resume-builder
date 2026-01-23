class ResumeUploader {

    async detectAndSetup() {
        console.log('📂 Resume Uploader: Detecting file inputs...');

        // Find all file inputs that haven't been processed yet
        const fileInputs = document.querySelectorAll('input[type="file"]:not([data-smartjob-injected])');

        for (const input of fileInputs) {
            const label = this.findLabel(input);
            const labelText = label?.textContent.toLowerCase() || '';
            const inputName = input.name?.toLowerCase() || '';
            const placeholder = input.placeholder?.toLowerCase() || '';

            // Check if it's for resume/CV
            if (labelText.includes('resume') ||
                labelText.includes('cv') ||
                labelText.includes('curriculum') ||
                inputName.includes('resume') ||
                placeholder.includes('resume')) {

                console.log('✅ Found resume upload field');
                await this.addAutoUploadButton(input);
            }
        }
    }

    async addAutoUploadButton(fileInput) {
        // Mark as processed immediately
        fileInput.dataset.smartjobInjected = 'true';

        // Get current job info
        const { currentJob } = await chrome.storage.local.get('currentJob');

        if (!currentJob?.folder_path) {
            console.warn('⚠️ No current job folder - showing manual helper');
            this.addManualHelper(fileInput, null);
            return;
        }

        const resumePath = `${currentJob.folder_path}/NuthanReddy.pdf`;

        // Create auto-upload button
        const button = document.createElement('button');
        button.type = 'button'; // Prevent form submission
        button.textContent = '📂 Auto-Upload Resume';
        button.className = 'smartjobapply-auto-upload';
        button.style.cssText = `
      margin: 8px 8px 8px 0;
      padding: 10px 20px;
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 600;
      box-shadow: 0 2px 8px rgba(16,185,129,0.3);
      transition: all 0.2s;
    `;

        button.onmouseover = () => {
            button.style.transform = 'translateY(-1px)';
            button.style.boxShadow = '0 4px 12px rgba(16,185,129,0.4)';
        };

        button.onmouseout = () => {
            button.style.transform = 'translateY(0)';
            button.style.boxShadow = '0 2px 8px rgba(16,185,129,0.3)';
        };

        button.onclick = async (e) => {
            e.preventDefault();
            e.stopPropagation();

            button.disabled = true;
            button.textContent = '⏳ Uploading...';

            try {
                await this.autoUpload(fileInput, resumePath);

                button.textContent = '✅ Uploaded!';
                button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';

                // Mark field as filled
                fileInput.style.border = '2px solid #10b981';

            } catch (error) {
                console.error('Upload failed:', error);
                button.textContent = '❌ Failed';
                button.style.background = '#ef4444';

                setTimeout(() => {
                    button.textContent = '📂 Auto-Upload Resume';
                    button.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                    button.disabled = false;
                }, 3000);
            }
        };

        // Also add manual helper button (fallback)
        const manualButton = document.createElement('button');
        manualButton.type = 'button';
        manualButton.textContent = '📋 Copy Path';
        manualButton.style.cssText = `
      margin: 8px 0;
      padding: 10px 20px;
      background: #6b7280;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 600;
    `;

        manualButton.onclick = async (e) => {
            e.preventDefault();
            await navigator.clipboard.writeText(resumePath);
            manualButton.textContent = '✅ Copied!';
            setTimeout(() => {
                manualButton.textContent = '📋 Copy Path';
            }, 2000);
        };

        // Insert buttons
        const container = document.createElement('div');
        container.style.cssText = 'margin: 8px 0; display: flex; gap: 8px;';
        container.appendChild(button);
        container.appendChild(manualButton);

        fileInput.parentNode.insertBefore(container, fileInput.nextSibling);

        // Yellow border on input
        fileInput.style.border = '2px solid #f59e0b';
    }

    async autoUpload(fileInput, resumePath) {
        console.log('🚀 Starting auto-upload process...');

        // Step 1: Trigger file dialog by clicking input
        fileInput.click();

        // Step 2: Wait a moment for dialog to appear
        await this.sleep(500);

        // Step 3: Call native messaging to automate file picker
        const response = await chrome.runtime.sendNativeMessage(
            HOST_NAME,
            {
                action: 'upload_file',
                file_path: resumePath
            }
        );

        if (response.success) {
            console.log('✅ Auto-upload successful!');

            // Wait for file to be selected
            await this.sleep(1000);

            // Verify file was selected
            if (fileInput.files.length > 0) {
                console.log('✅ File input has file:', fileInput.files[0].name);

                // Trigger change event for form validation
                fileInput.dispatchEvent(new Event('change', { bubbles: true }));

                return true;
            } else {
                console.warn('⚠️ File input still empty after automation');
                throw new Error('File not selected');
            }

        } else {
            console.error('❌ Auto-upload failed:', response.error);
            throw new Error(response.error || 'Upload failed');
        }
    }

    addManualHelper(fileInput, resumePath) {
        // Fallback to manual copy-paste helper
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = '📋 Copy Resume Path';
        button.style.cssText = `
      margin: 8px 0;
      padding: 10px 20px;
      background: #f59e0b;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 600;
    `;

        button.onclick = async (e) => {
            e.preventDefault();
            if (resumePath) {
                await navigator.clipboard.writeText(resumePath);
                button.textContent = '✅ Path Copied!';
                setTimeout(() => {
                    button.textContent = '📋 Copy Resume Path';
                }, 2000);
            }
        };

        fileInput.parentNode.insertBefore(button, fileInput.nextSibling);
        fileInput.style.border = '2px solid #f59e0b';
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    findLabel(element) {
        if (element.id) {
            const label = document.querySelector(`label[for="${element.id}"]`);
            if (label) return label;
        }

        let parent = element.parentElement;
        while (parent && parent.tagName !== 'FORM') {
            const label = parent.querySelector('label');
            if (label) return label;
            parent = parent.parentElement;
        }

        return null;
    }
}

// Initialize on page load
const init = async () => {
    const uploader = new ResumeUploader();
    await uploader.detectAndSetup();

    // Observer for dynamic content (SPAs)
    const observer = new MutationObserver((mutations) => {
        let shouldCheck = false;
        for (const mutation of mutations) {
            if (mutation.addedNodes.length > 0) {
                shouldCheck = true;
                break;
            }
        }
        if (shouldCheck) {
            uploader.detectAndSetup();
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
