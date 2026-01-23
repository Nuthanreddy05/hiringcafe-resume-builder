/**
 * detector.js
 * Identifies which ATS platform the user is currently on.
 */

window.ATSDetector = {
    platforms: {
        GREENHOUSE: 'greenhouse',
        LEVER: 'lever',
        WORKDAY: 'workday',
        TALEO: 'taleo',
        SMARTRECRUITERS: 'smartrecruiters',
        ASHBY: 'ashby',
        UNKNOWN: 'unknown'
    },

    getPlatform: function () {
        const url = window.location.href.toLowerCase();
        const hostname = window.location.hostname;

        // 1. URL-based detection
        if (hostname.includes('greenhouse.io') ||
            url.includes('boards.greenhouse.io') ||
            document.querySelector('#greenhouse-application')) {
            return this.platforms.GREENHOUSE;
        }

        if (hostname.includes('lever.co') ||
            url.includes('jobs.lever.co')) {
            return this.platforms.LEVER;
        }

        if (hostname.includes('myworkdayjobs.com')) {
            return this.platforms.WORKDAY;
        }

        if (hostname.includes('taleo.net')) {
            return this.platforms.TALEO;
        }

        if (hostname.includes('smartrecruiters.com')) {
            return this.platforms.SMARTRECRUITERS;
        }

        if (hostname.includes('ashbyhq.com')) {
            return this.platforms.ASHBY;
        }

        // 2. DOM-based fallbacks (if using custom domains)
        if (document.querySelector('div[id^="greenhouse"]')) return this.platforms.GREENHOUSE;
        if (document.querySelector('meta[content*="Lever"]')) return this.platforms.LEVER;

        return this.platforms.UNKNOWN;
    }
};

console.log("🕵️ SmartJobApply Detector Loaded. Platform:", window.ATSDetector.getPlatform());
