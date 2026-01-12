import logging

logger = logging.getLogger("ATS_Handlers")

class ATSHandler:
    """Base Handler Interface."""
    def scrape_context(self, page):
        """Returns (role, description)"""
        return "", ""
    
    def find_resume_input(self, page):
        """Returns locator for resume upload"""
        return None

class GreenhouseHandler(ATSHandler):
    def scrape_context(self, page):
        try:
            # 1. Try generic H1 (works on most Greenhouse)
            role = page.locator("h1, .app-title, #app_title").first.inner_text().strip()
            # 2. Description
            desc = page.locator("#content, #main, .content-intro").first.inner_text().strip()[:3000]
            return role, desc
        except:
            return "", ""

    def find_resume_input(self, page):
        # Greenhouse often hides the input. Target generic file input if #resume missing.
        loc = page.locator("#resume, input[id*='resume'], input[type='file']").first
        return loc

class LeverHandler(ATSHandler):
    def scrape_context(self, page):
        try:
            role = page.locator(".posting-headline h2, h2.posting-headline, h2").first.inner_text().strip()
            desc = page.locator(".posting-content, .content, div[data-qa='job-description']").first.inner_text().strip()[:3000]
            return role, desc
        except:
            return "", ""

    def find_resume_input(self, page):
        # 1. Explicit name
        loc = page.locator("input[name='resume']")
        if loc.count() > 0: return loc.first
        # 2. Generic fallback
        return page.locator("input[type='file']").first

class AshbyHandler(ATSHandler):
    def scrape_context(self, page):
        try:
            role = page.locator("h1, .job-title, [class*='JobTitle']").first.inner_text().strip()
            desc = page.locator(".job-description, section, div[class*='Description']").first.inner_text().strip()[:3000]
            return role, desc
        except:
            return "", ""

    def find_resume_input(self, page):
        return page.locator("input[type='file']").first

class GenericHandler(ATSHandler):
    def scrape_context(self, page):
        # Heuristics
        try:
            role = page.locator("h1, h2").first.inner_text().strip()
            desc = page.locator("body").inner_text().strip()[:3000]
            return role, desc
        except:
            return "", ""

    def find_resume_input(self, page):
        return page.locator("input[type='file']").first

class ATSDetector:
    @staticmethod
    def get_handler(url: str):
        u = url.lower()
        if "greenhouse.io" in u:
            return GreenhouseHandler()
        elif "lever.co" in u:
            return LeverHandler()
        elif "ashbyhq.com" in u:
            return AshbyHandler()
        
        return GenericHandler()
