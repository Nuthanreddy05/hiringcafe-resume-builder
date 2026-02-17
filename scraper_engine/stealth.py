import random
import time
import asyncio
from playwright.async_api import async_playwright

# Common User Agents (Desktop)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
]

class StealthScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.context = None

    async def start(self):
        """Initialize the browser with stealth settings."""
        self.playwright = await async_playwright().start()
        # Launch Browser (Chromium)
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars"
            ]
        )
        await self._create_stealth_context()

    async def _create_stealth_context(self):
        """Create a browser context with randomized fingerprints."""
        user_agent = random.choice(USER_AGENTS)
        
        # Viewport randomization
        width = 1920 + random.randint(-50, 50)
        height = 1080 + random.randint(-50, 50)
        
        self.context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={"width": width, "height": height},
            locale="en-US",
            timezone_id="America/New_York",
            # Permissions mostly denied to mimic strict user
            permissions=[] 
        )
        
        # Apply JS Evasions (The "Patent Code" logic from puppeteer-extra-stealth)
        await self.context.add_init_script("""
            // 1. Mask WebDriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // 2. Mock Chrome Runtime
            window.chrome = { runtime: {} };
            
            // 3. Mock Plugins
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            
            // 4. Mock Languages
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            
            // 5. Hardware Concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 4 });
        """)

    async def scrape_url(self, url):
        """Scrape a single URL with random delays."""
        page = None
        try:
            page = await self.context.new_page()
            
            # Rate Limit Delay (The "Scab Delay" start)
            await self.human_delay(2, 5) 
            
            print(f"🕵️  Stealth Visiting: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for dynamic content (JSON-LD often injected by JS)
            await self.human_delay(3, 7)
            
            # Scroll to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            await self.human_delay(1, 3)
            
            content = await page.content()
            return content
            
        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
            return None
        finally:
            if page:
                await page.close()

    async def close(self):
        """Clean up resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def human_delay(self, min_s=1, max_s=3):
        """Randomized sleep to mimic human behavior."""
        delay = random.uniform(min_s, max_s)
        await asyncio.sleep(delay)

# Simple test execution
if __name__ == "__main__":
    async def test():
        scraper = StealthScraper(headless=True)
        await scraper.start()
        html = await scraper.scrape_url("https://www.google.com") # Test on a strict site
        if html and "google" in html.lower():
            print("✅ Scraping Successful (Stealth passed basic load)")
        else:
            print("❌ Scraping Failed")
        await scraper.close()

    asyncio.run(test())
