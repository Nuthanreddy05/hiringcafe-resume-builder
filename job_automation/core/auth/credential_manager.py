import yaml
from pathlib import Path
from typing import Dict

class CredentialManager:
    """Secure credential loading and validation"""
    
    def __init__(self, credentials_file: Path = Path("job_automation/config/credentials.yaml")):
        self.credentials_file = credentials_file
        self._credentials = {}
        # Try loading immediately, but don't crash if file missing yet (setup script might handle it)
        try:
            self._load_credentials()
        except FileNotFoundError:
            print(f"⚠️ Warning: Credentials file not found at {self.credentials_file}")
    
    def _load_credentials(self):
        """Load credentials from YAML file"""
        if not self.credentials_file.exists():
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_file}\n"
                f"Please create it from credentials.yaml.example"
            )
        
        with open(self.credentials_file, 'r') as f:
            self._credentials = yaml.safe_load(f) or {}
    
    def get_credentials(self, source: str) -> Dict:
        """Get credentials for a specific source"""
        if source not in self._credentials:
            raise ValueError(
                f"No credentials found for '{source}' in {self.credentials_file}\n"
                f"Available sources: {list(self._credentials.keys())}"
            )
        
        return self._credentials[source]
    
    def validate_credentials(self, source: str, method: str) -> bool:
        """Validate that required credential fields are present"""
        creds = self.get_credentials(source)
        
        if method == 'email':
            required = ['email', 'password']
        elif method == 'google':
            required = ['google_email', 'google_password']
        elif method == 'linkedin':
            required = ['linkedin_email', 'linkedin_password']
        else:
            raise ValueError(f"Unknown auth method: {method}")
        
        missing = [field for field in required if not creds.get(field)]
        
        if missing:
            raise ValueError(f"Missing required credentials for {source}/{method}: {missing}")
        
        return True
