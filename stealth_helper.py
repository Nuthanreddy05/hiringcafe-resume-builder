
# Javascript evasions to mask headless automation
# Derived from puppeteer-extra-plugin-stealth

def get_stealth_scripts():
    return [
        """
        // 1. Pass the Webdriver Test
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        """,
        """
        // 2. Mock Chrome Object
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
        """,
        """
        // 3. Mock Permissions Query
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({ state: 'denied' }) :
            originalQuery(parameters)
        );
        """,
        """
        // 4. Mock Plugins (Critical for Headless)
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        """,
        """
        // 5. Hide Automation Features from Modern Detection
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // Spoof Unmasked Vendor/Renderer if needed
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameter(parameter);
        };
        """
    ]

# Human interaction helpers
import time
import random

def human_sleep(min_ms=500, max_ms=1500):
    time.sleep(random.randint(min_ms, max_ms) / 1000.0)

def human_type(element, text, delay_ms=30):
    """Type with variable delay between keystrokes"""
    element.focus()
    for char in text:
        element.type(char, delay=random.randint(delay_ms, delay_ms + 50))
        # rare pauses
        if random.random() < 0.05:
            time.sleep(random.random() * 0.2)
            
def human_click(page, element):
    """Move to element and click"""
    box = element.bounding_box()
    if box:
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2
        # Jitter
        x += random.randint(-5, 5)
        y += random.randint(-5, 5)
        
        page.mouse.move(x, y, steps=10)
        time.sleep(random.uniform(0.1, 0.3))
        page.mouse.down()
        time.sleep(random.uniform(0.05, 0.15))
        page.mouse.up()
    else:
        element.click(force=True)
