"""
Enhanced Stealth Browser using Playwright.
Implements all anti-detection techniques to avoid bot detection.
"""
import asyncio
import random
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from config.settings import SCRAPING, USER_AGENTS, PROXY


class StealthBrowser:
    """
    A stealth browser wrapper that evades common bot detection techniques.

    Features:
    - Randomized user agents
    - Randomized viewport sizes
    - WebDriver flag masking
    - Canvas/WebGL fingerprint noise
    - Human-like delays and mouse movements
    - Proxy support with rotation
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.current_user_agent = None

    async def start(self) -> None:
        """Initialize the browser with stealth settings."""
        self.playwright = await async_playwright().start()

        # Browser launch arguments for stealth
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
            "--window-size=1920,1080",
            "--start-maximized",
            "--ignore-certificate-errors",
            "--ignore-certificate-errors-spki-list",
        ]

        # Add proxy if configured
        proxy_config = None
        if self.proxy:
            proxy_config = {"server": self.proxy}
        elif PROXY.get("enabled") and PROXY.get("proxies"):
            proxy_url = random.choice(PROXY["proxies"])
            proxy_config = {"server": proxy_url}

        # Launch browser
        browser_type = getattr(self.playwright, SCRAPING.get("browser_type", "chromium"))
        self.browser = await browser_type.launch(
            headless=self.headless,
            args=launch_args,
            proxy=proxy_config,
        )

        # Create stealth context
        await self._create_stealth_context()

    async def _create_stealth_context(self) -> None:
        """Create a browser context with randomized fingerprints."""
        # Select random user agent
        self.current_user_agent = random.choice(USER_AGENTS)

        # Randomize viewport (slight variations to avoid fingerprinting)
        width = 1920 + random.randint(-100, 100)
        height = 1080 + random.randint(-50, 50)

        # Randomize color depth and device scale factor
        device_scale_factor = random.choice([1, 1.25, 1.5, 2])

        self.context = await self.browser.new_context(
            user_agent=self.current_user_agent,
            viewport={"width": width, "height": height},
            device_scale_factor=device_scale_factor,
            locale="en-US",
            timezone_id=random.choice([
                "America/New_York",
                "America/Chicago",
                "America/Los_Angeles",
                "America/Denver",
            ]),
            permissions=["geolocation"],  # Some sites check for this
            color_scheme="light",
            has_touch=False,
            is_mobile=False,
            java_script_enabled=True,
        )

        # Add stealth scripts to every page
        await self.context.add_init_script(self._get_stealth_script())

    def _get_stealth_script(self) -> str:
        """Return JavaScript to inject for stealth mode."""
        return """
        // =================================================================
        // STEALTH SCRIPT - Evade bot detection
        // =================================================================

        // 1. Mask WebDriver flag (most common detection)
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });

        // Also delete it from the prototype
        delete Navigator.prototype.webdriver;

        // 2. Mock Chrome runtime (Chrome-specific check)
        window.chrome = {
            runtime: {},
            loadTimes: function() { return {}; },
            csi: function() { return {}; },
            app: { isInstalled: false }
        };

        // 3. Mock plugins (real browsers have plugins)
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ];
                plugins.item = (index) => plugins[index];
                plugins.namedItem = (name) => plugins.find(p => p.name === name);
                plugins.refresh = () => {};
                return plugins;
            },
            configurable: true
        });

        // 4. Mock languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'es'],
            configurable: true
        });

        // 5. Mock hardware concurrency (CPU cores)
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => Math.floor(Math.random() * 4) + 4,  // 4-8 cores
            configurable: true
        });

        // 6. Mock device memory
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => Math.pow(2, Math.floor(Math.random() * 3) + 2),  // 4, 8, or 16 GB
            configurable: true
        });

        // 7. Mock permissions API
        const originalQuery = window.navigator.permissions?.query;
        if (originalQuery) {
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        }

        // 8. Canvas fingerprint noise (adds random noise to canvas)
        const originalGetContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, ...args) {
            const context = originalGetContext.call(this, type, ...args);
            if (type === '2d' && context) {
                const originalFillText = context.fillText.bind(context);
                context.fillText = function(text, x, y, ...rest) {
                    // Add tiny random offset
                    const offsetX = (Math.random() - 0.5) * 0.01;
                    const offsetY = (Math.random() - 0.5) * 0.01;
                    return originalFillText(text, x + offsetX, y + offsetY, ...rest);
                };
            }
            return context;
        };

        // 9. WebGL fingerprint masking
        const getParameterProxyHandler = {
            apply: function(target, thisArg, args) {
                const param = args[0];
                const result = Reflect.apply(target, thisArg, args);

                // Mask renderer and vendor strings
                if (param === 37445) {  // UNMASKED_VENDOR_WEBGL
                    return 'Intel Inc.';
                }
                if (param === 37446) {  // UNMASKED_RENDERER_WEBGL
                    return 'Intel Iris OpenGL Engine';
                }
                return result;
            }
        };

        const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = new Proxy(originalGetParameter, getParameterProxyHandler);

        if (typeof WebGL2RenderingContext !== 'undefined') {
            const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = new Proxy(originalGetParameter2, getParameterProxyHandler);
        }

        // 10. Audio fingerprint noise
        const originalCreateOscillator = AudioContext.prototype.createOscillator;
        AudioContext.prototype.createOscillator = function() {
            const oscillator = originalCreateOscillator.call(this);
            oscillator.frequency.value += (Math.random() - 0.5) * 0.01;
            return oscillator;
        };

        // 11. Mock connection info
        Object.defineProperty(navigator, 'connection', {
            get: () => ({
                effectiveType: '4g',
                rtt: Math.floor(Math.random() * 50) + 50,
                downlink: Math.random() * 5 + 5,
                saveData: false
            }),
            configurable: true
        });

        // 12. Prevent iframe detection
        Object.defineProperty(window, 'frameElement', {
            get: () => null,
            configurable: true
        });

        // 13. Mock screen properties to avoid fingerprinting
        const screenProps = {
            availWidth: window.screen.width,
            availHeight: window.screen.height - 40,  // Account for taskbar
            colorDepth: 24,
            pixelDepth: 24
        };
        for (const [prop, value] of Object.entries(screenProps)) {
            Object.defineProperty(window.screen, prop, {
                get: () => value,
                configurable: true
            });
        }

        // 14. Console.debug trap (some sites check for automation via console)
        const originalDebug = console.debug;
        console.debug = function(...args) {
            if (args[0]?.includes?.('automation') || args[0]?.includes?.('webdriver')) {
                return;
            }
            return originalDebug.apply(this, args);
        };

        console.log('🕵️ Stealth mode activated');
        """

    async def new_page(self) -> Page:
        """Create a new page with stealth settings."""
        if not self.context:
            await self.start()

        page = await self.context.new_page()

        # Set extra HTTP headers
        await page.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        })

        return page

    async def goto(self, page: Page, url: str, wait_until: str = "domcontentloaded") -> bool:
        """
        Navigate to URL with human-like behavior.

        Args:
            page: Playwright page object
            url: URL to navigate to
            wait_until: When to consider navigation complete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Random delay before navigation (human-like)
            await self.human_delay(0.5, 1.5)

            # Navigate
            response = await page.goto(
                url,
                wait_until=wait_until,
                timeout=SCRAPING["page_load_timeout"] * 1000
            )

            if not response:
                return False

            # Check for common block indicators
            status = response.status
            if status in [403, 429, 503]:
                print(f"⚠️  Blocked or rate limited: {status}")
                return False

            # Wait a bit for dynamic content
            await self.human_delay(1, 2)

            # Simulate human scrolling
            await self.simulate_human_behavior(page)

            return True

        except Exception as e:
            print(f"❌ Navigation error: {e}")
            return False

    async def simulate_human_behavior(self, page: Page) -> None:
        """Simulate human-like browsing behavior."""
        try:
            # Random scroll patterns
            scroll_actions = random.randint(2, 4)
            for _ in range(scroll_actions):
                # Scroll down
                scroll_amount = random.randint(200, 500)
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                await self.human_delay(0.3, 0.8)

            # Sometimes scroll back up a bit
            if random.random() > 0.5:
                await page.evaluate(f"window.scrollBy(0, -{random.randint(100, 200)})")
                await self.human_delay(0.2, 0.5)

            # Random mouse movement (if not headless)
            if not self.headless:
                try:
                    viewport = page.viewport_size
                    if viewport:
                        x = random.randint(100, viewport["width"] - 100)
                        y = random.randint(100, viewport["height"] - 100)
                        await page.mouse.move(x, y)
                except:
                    pass

        except Exception:
            pass  # Non-critical, continue

    async def human_delay(self, min_seconds: float = None, max_seconds: float = None) -> None:
        """Add a random delay to mimic human behavior."""
        if min_seconds is None:
            min_seconds = SCRAPING["min_delay_between_requests"]
        if max_seconds is None:
            max_seconds = SCRAPING["max_delay_between_requests"]

        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    async def get_page_content(self, page: Page) -> str:
        """Get the full HTML content of the page."""
        return await page.content()

    async def wait_for_selector(
        self,
        page: Page,
        selector: str,
        timeout: int = None
    ) -> bool:
        """Wait for a selector to appear on the page."""
        if timeout is None:
            timeout = SCRAPING["element_wait_timeout"] * 1000
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return True
        except:
            return False

    async def wait_for_any_selector(
        self,
        page: Page,
        selectors: list,
        timeout: int = None
    ) -> Optional[str]:
        """Wait for any of the given selectors to appear."""
        if timeout is None:
            timeout = SCRAPING["element_wait_timeout"] * 1000

        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=timeout // len(selectors))
                return selector
            except:
                continue
        return None

    async def scroll_to_bottom(self, page: Page, max_scrolls: int = 10) -> None:
        """Scroll to the bottom of the page to load all content."""
        for _ in range(max_scrolls):
            # Get current height
            prev_height = await page.evaluate("document.body.scrollHeight")

            # Scroll down
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.human_delay(1, 2)

            # Check if we've reached the bottom
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == prev_height:
                break

    async def close(self) -> None:
        """Clean up resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# =============================================================================
# Convenience function for quick scraping
# =============================================================================
async def scrape_url(url: str, headless: bool = True) -> Optional[str]:
    """
    Quick helper to scrape a single URL.

    Args:
        url: URL to scrape
        headless: Run in headless mode

    Returns:
        HTML content or None if failed
    """
    async with StealthBrowser(headless=headless) as browser:
        page = await browser.new_page()
        success = await browser.goto(page, url)
        if success:
            return await browser.get_page_content(page)
        return None


# =============================================================================
# Test
# =============================================================================
if __name__ == "__main__":
    async def test():
        print("🧪 Testing StealthBrowser...")

        async with StealthBrowser(headless=True) as browser:
            page = await browser.new_page()

            # Test on a bot detection site
            print("Testing bot detection evasion...")
            success = await browser.goto(page, "https://bot.sannysoft.com/")

            if success:
                # Take screenshot for verification
                await page.screenshot(path="stealth_test.png")
                print("✅ Test passed! Check stealth_test.png")
            else:
                print("❌ Navigation failed")

    asyncio.run(test())
