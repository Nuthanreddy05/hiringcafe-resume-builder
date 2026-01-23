// Background Service Worker
// Handles Native Messaging Relay

chrome.runtime.onInstalled.addListener(() => {
    console.log("SmartJobApply Extension Installed");
});

// Proxy content script messages to Native Host
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "generate_answer") {
        console.log("🤖 Asking AI:", request.question);

        // Send to Native Host (com.smartjobapply.folder_reader)
        chrome.runtime.sendNativeMessage(
            'com.smartjobapply.folder_reader',
            request,
            (response) => {
                if (chrome.runtime.lastError) {
                    console.error("Native Host Error:", chrome.runtime.lastError.message);
                    sendResponse({ error: chrome.runtime.lastError.message });
                } else {
                    console.log("AI Answer Received:", response);
                    sendResponse(response);
                }
            }
        );
        return true; // Keep channel open for async response
    }
});
