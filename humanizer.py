import time
import random
import math

class Humanizer:
    """
    Simulates human behavior to avoid detection.
    Priority: Stealth > Speed
    """
    
    def __init__(self, page):
        self.page = page

    def type_like_human(self, element, text):
        """Type with natural rhythm and occasional errors."""
        # Ensure focus
        element.click(force=True)
        self.pause("before_typing")
        
        for i, char in enumerate(text):
            # Type character
            element.type(char)
            
            # Variable speed (faster for common words)
            if char == ' ':  # Space = word boundary
                delay = random.uniform(0.12, 0.20)
            else:
                delay = random.uniform(0.04, 0.12)
            
            # Occasional typo (1% chance)
            if random.random() < 0.01:
                time.sleep(0.1)
                element.press("Backspace")
                time.sleep(0.15)
                element.type(char)
            
            time.sleep(delay)
    
    def move_and_click(self, element, force=False):
        """Click with natural mouse movement."""
        box = element.bounding_box()
        if not box:
            # Fallback for hidden/tricky elements
            element.click(force=force)
            return

        # Current mouse position (random start if unknown)
        # Note: Playwright doesn't expose current mouse pos easily without tracking, 
        # so we assume last known or center of screen relative.
        # Ideally, we just move from A to B.
        
        # Target with randomized offset
        target_x = box['x'] + box['width']/2 + random.uniform(-10, 10)
        target_y = box['y'] + box['height']/2 + random.uniform(-5, 5)
        
        # We start from a random point "near" the element or screen center to simulate approach
        start_x = target_x + random.uniform(-200, 200)
        start_y = target_y + random.uniform(-200, 200)
        
        self.page.mouse.move(start_x, start_y)
        self._move_mouse_bezier(start_x, start_y, target_x, target_y)
        
        # Pause before click (humans don't click instantly)
        self.pause("after_move")
        element.click(force=force)
        self.pause("after_click")

    def _move_mouse_bezier(self, x1, y1, x2, y2):
        """Move mouse along bezier curve."""
        # Control point (creates curve)
        cp_x = (x1 + x2) / 2 + random.uniform(-50, 50)
        cp_y = (y1 + y2) / 2 + random.uniform(-50, 50)
        
        steps = random.randint(10, 20)
        for i in range(steps + 1):
            t = i / steps
            
            # Bezier formula
            x = (1-t)**2 * x1 + 2*(1-t)*t * cp_x + t**2 * x2
            y = (1-t)**2 * y1 + 2*(1-t)*t * cp_y + t**2 * y2
            
            self.page.mouse.move(x, y)
            time.sleep(random.uniform(0.005, 0.015))
    
    def pause(self, action_type):
        """Human pauses between actions."""
        delays = {
            "reading": (2.0, 4.5),
            "thinking": (1.0, 3.0),
            "before_typing": (0.5, 1.2),
            "after_move": (0.1, 0.3),
            "after_click": (0.5, 1.5),
            "scrolling": (0.3, 0.8)
        }
        
        min_t, max_t = delays.get(action_type, (0.5, 1.0))
        time.sleep(random.uniform(min_t, max_t))
    
    def scroll_naturally(self, element):
        """Scroll with human-like behavior."""
        if not element: return
        try:
            box = element.bounding_box()
            if not box: 
                element.scroll_into_view_if_needed()
                return
                
            current_idx = random.randint(3, 6)
            for _ in range(current_idx):
                self.page.mouse.wheel(0, random.randint(50, 150))
                time.sleep(random.uniform(0.1, 0.3))
                
            element.scroll_into_view_if_needed()
        except:
             element.scroll_into_view_if_needed()
