// popup.js

const HOST_NAME = 'com.smartjobapply.folder_reader';
const UI = {
    loading: document.getElementById('loading-view'),
    error: document.getElementById('error-view'),
    empty: document.getElementById('empty-view'),
    list: document.getElementById('job-list'),
    errorMsg: document.querySelector('.error-msg'),
    retryBtn: document.getElementById('retry-btn'),
    settingsBtn: document.getElementById('settings-btn'),
    statusText: document.getElementById('status-text')
};

// Utils
const showView = (viewName) => {
    Object.values(UI).forEach(el => {
        if (el instanceof HTMLElement && el.id && el.id.includes('view')) {
            el.classList.add('hidden');
        }
    });
    UI.list.classList.add('hidden'); // Ensure list is hidden

    if (viewName === 'loading') UI.loading.classList.remove('hidden');
    if (viewName === 'error') UI.error.classList.remove('hidden');
    if (viewName === 'empty') UI.empty.classList.remove('hidden');
    if (viewName === 'list') UI.list.classList.remove('hidden');
};

const showError = (msg) => {
    UI.errorMsg.textContent = msg;
    showView('error');
    UI.statusText.textContent = "Error";
};

const formatDate = (isoString) => {
    try {
        const date = new Date(isoString);
        return new Intl.DateTimeFormat('en-US', {
            month: 'short', day: 'numeric',
            hour: 'numeric', minute: 'numeric'
        }).format(date);
    } catch (e) {
        return '';
    }
};

const openSettings = () => {
    chrome.runtime.openOptionsPage();
};

const toggleJobStatus = (folderPath, currentStatus) => {
    const newStatus = currentStatus === 'applied' ? 'pending' : 'applied';

    // Optimistic UI update
    UI.statusText.textContent = "Updating...";

    chrome.runtime.sendNativeMessage(
        HOST_NAME,
        {
            action: 'update_status',
            folder_path: folderPath,
            status: newStatus
        },
        (response) => {
            if (response && response.success) {
                fetchJobs(); // Reload list
            } else {
                showError("Failed to update status");
            }
        }
    );
};

const renderJobs = (jobs) => {
    UI.list.innerHTML = '';

    jobs.forEach(job => {
        const card = document.createElement('div');
        const isApplied = job.status === 'applied';
        card.className = isApplied ? 'job-card applied' : 'job-card';

        const btnText = isApplied ? 'Re-Apply' : 'Apply Now';
        const statusIcon = isApplied ? '✅' : '⬜';
        const statusTitle = isApplied ? 'Mark as Pending' : 'Mark as Applied';

        card.innerHTML = `
            <div class="job-header">
                <span class="company">${job.company}</span>
                <span class="date">${formatDate(job.created_at)}</span>
            </div>
            <span class="title">${job.job_title}</span>
            <div class="actions">
                <span class="platform-badge ${job.platform}">${job.platform}</span>
                <div class="btn-group">
                    <button class="status-btn" title="${statusTitle}">${statusIcon}</button>
                    <button class="apply-btn" data-url="${job.apply_url}">${btnText}</button>
                </div>
            </div>
        `;

        // Apply Button Handler
        const applyBtn = card.querySelector('.apply-btn');
        applyBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const url = applyBtn.dataset.url;
            if (url) {
                // Save context for Resume Uploader
                chrome.storage.local.set({ currentJob: job });
                chrome.tabs.create({ url: url });
            } else {
                alert("No Apply URL found for this job.");
            }
        });

        // Status Button Handler
        const statusBtn = card.querySelector('.status-btn');
        statusBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleJobStatus(job.folder_path, job.status || 'pending');
        });

        UI.list.appendChild(card);
    });

    showView('list');

    // Count stats
    const appliedCount = jobs.filter(j => j.status === 'applied').length;
    const pendingCount = jobs.length - appliedCount;
    UI.statusText.textContent = `${pendingCount} Pending • ${appliedCount} Applied`;
};

const fetchJobs = () => {
    showView('loading');
    UI.statusText.textContent = "Connecting...";

    console.log("Sending message to native host...");

    try {
        chrome.runtime.sendNativeMessage(
            HOST_NAME,
            { action: 'get_jobs' },
            (response) => {
                if (chrome.runtime.lastError) {
                    console.error("Native Messaging Error:", chrome.runtime.lastError.message);
                    showError("Native Host Error: " + chrome.runtime.lastError.message);
                    return;
                }

                if (!response) {
                    showError("No response from Native Host.");
                    return;
                }

                if (response.error) {
                    showError("Host Error: " + response.error);
                    return;
                }

                if (response.jobs && response.jobs.length > 0) {
                    renderJobs(response.jobs);
                } else {
                    showView('empty');
                    UI.statusText.textContent = "0 Jobs";
                }
            }
        );
    } catch (e) {
        console.error("Exception:", e);
        showError("Extension Error: " + e.message);
    }
};

// Listeners
document.addEventListener('DOMContentLoaded', fetchJobs);
UI.retryBtn.addEventListener('click', fetchJobs);
UI.settingsBtn.addEventListener('click', openSettings);
