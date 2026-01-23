from abc import ABC, abstractmethod
from playwright.sync_api import BrowserContext, Page
from pathlib import Path
import json

class BaseAuthenticator(ABC):
    """Abstract base class for authentication"""
    
    def __init__(self, context: BrowserContext, credentials: dict, session_dir: Path):
        self.context = context
        self.credentials = credentials
        self.session_dir = session_dir
        self.session_file = session_dir / f"{self.get_source_name()}_session.json"
        self.is_authenticated = False
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return source name (e.g., 'jobright')"""
        pass
    
    @abstractmethod
    def login(self, page: Page) -> bool:
        """
        Perform login flow
        Returns: True if login successful, False otherwise
        """
        pass
    
    @abstractmethod
    def verify_authenticated(self, page: Page) -> bool:
        """
        Check if currently authenticated
        Returns: True if authenticated, False otherwise
        """
        pass
    
    def save_session(self):
        """Save cookies and storage state for session persistence"""
        print(f"   💾 Saving {self.get_source_name()} session...")
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Save browser context state (cookies, localStorage, sessionStorage)
        self.context.storage_state(path=str(self.session_file))
        print(f"   ✓ Session saved to {self.session_file}")
    
    def load_session(self) -> bool:
        """
        Load saved session
        Returns: True if session loaded, False if no session found
        """
        if not self.session_file.exists():
            print(f"   ⚠️  No saved session found at {self.session_file}")
            return False
        
        print(f"   🔄 Loading saved session from {self.session_file}")
        try:
            # Context state was already loaded when creating context
            # Just verify it's still valid
            page = self.context.new_page()
            authenticated = self.verify_authenticated(page)
            page.close()
            
            if authenticated:
                print(f"   ✓ Session loaded successfully")
                self.is_authenticated = True
                return True
            else:
                print(f"   ⚠️  Session expired or invalid")
                return False
        except Exception as e:
            print(f"   ✗ Failed to load session: {e}")
            return False
    
    def authenticate(self) -> bool:
        """
        Main authentication flow:
        1. Try to load existing session
        2. If session invalid, perform fresh login
        3. Save new session
        """
        print(f"\n🔐 Authenticating with {self.get_source_name().upper()}...")
        
        # Try loading existing session first
        if self.load_session():
            return True
        
        # No valid session, perform fresh login
        print(f"   🔑 Performing fresh login...")
        page = self.context.new_page()
        
        try:
            success = self.login(page)
            
            if success:
                print(f"   ✅ Login successful!")
                self.save_session()
                self.is_authenticated = True
                return True
            else:
                print(f"   ✗ Login failed")
                return False
        finally:
            page.close()
