"""
Security validator for job application URLs and data.
Prevents malicious URLs and path traversal attacks.
"""

import re
from urllib.parse import urlparse
from pathlib import Path

class SecurityValidator:
    """Validates URLs and data before processing."""
    
    # Whitelist of approved job board domains
    APPROVED_DOMAINS = {
        'greenhouse.io',
        'job-boards.greenhouse.io',
        'boards.greenhouse.io',
        'lever.co',
        'jobs.lever.co',
        'taleo.net',
        'tas-uhg.taleo.net',
        'tas-cognizant.taleo.net',
        'myworkdayjobs.com',
        'wd5.myworkdayjobs.com',
        'smartrecruiters.com',
        'jobs.smartrecruiters.com',
        'ashbyhq.com',
        'jobs.ashbyhq.com',
        'bamboohr.com',
        'icims.com',
        'jobvite.com',
        'brassring.com',
        'paylocity.com',
        'hiringcafe.com',
        'linkedin.com',
        'indeed.com',
        'glassdoor.com',
        'monster.com',
        'ziprecruiter.com'
    }
    
    # Dangerous patterns to block
    BLOCKED_PATTERNS = [
        r'javascript:',           # JavaScript execution
        r'data:',                 # Data URLs
        r'file://',              # Local file access
        r'\.\./\.\.',            # Path traversal
        r'<script',              # XSS attempts
        r'onclick=',             # Event handlers
        r'onerror=',
        r'onload=',
        r'\.exe$',               # Executables
        r'\.bat$',
        r'\.sh$',
        r'\.cmd$',
        r'\.ps1$'
    ]
    
    @classmethod
    def validate_url(cls, url):
        """
        Validate job URL for security.
        
        Returns:
            tuple: (is_valid: bool, reason: str)
        """
        if not url or not isinstance(url, str):
            return False, "Empty or invalid URL"
        
        url = url.strip()
        
        # Check for blocked patterns
        for pattern in cls.BLOCKED_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return False, f"Blocked pattern: {pattern}"
        
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            return False, f"URL parse error: {str(e)}"
        
        # Must have valid scheme
        if parsed.scheme not in ['http', 'https']:
            return False, f"Invalid scheme: {parsed.scheme} (only http/https allowed)"
        
        # Must have domain
        if not parsed.netloc:
            return False, "No domain found"
        
        # Extract domain
        domain = parsed.netloc.lower()
        
        # Remove port if present
        if ':' in domain:
            domain = domain.split(':')[0]
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Check against whitelist
        is_approved = False
        for approved_domain in cls.APPROVED_DOMAINS:
            if domain == approved_domain or domain.endswith('.' + approved_domain):
                is_approved = True
                break
        
        if not is_approved:
            return False, f"Domain not approved: {domain}"
        
        return True, "Valid URL"
    
    @classmethod
    def validate_folder_path(cls, path):
        """
        Validate folder path to prevent path traversal.
        
        Returns:
            tuple: (is_valid: bool, reason: str)
        """
        try:
            path_obj = Path(path)
            path_str = str(path_obj.absolute())
        except Exception as e:
            return False, f"Path error: {str(e)}"
        
        # Block path traversal attempts
        if '..' in str(path):
            return False, "Path traversal detected (..)"
        
        # Must contain expected base directories
        expected_bases = [
            'Desktop/Google Auto',
            'Desktop/Google Auto Internet',
            'CERTIFICATES/google',
            '/Users/',
            '/home/'
        ]
        
        has_valid_base = any(base in path_str for base in expected_bases)
        if not has_valid_base:
            return False, f"Invalid base directory"
        
        # Must not contain system directories
        blocked_dirs = [
            '/etc/',
            '/bin/',
            '/usr/bin/',
            '/System/',
            'C:\\Windows',
            'C:\\Program Files'
        ]
        
        for blocked in blocked_dirs:
            if blocked in path_str:
                return False, f"Blocked system directory: {blocked}"
        
        return True, "Valid path"
    
    @classmethod
    def sanitize_text(cls, text):
        """
        Sanitize text input to prevent XSS.
        
        Args:
            text: Input text to sanitize
            
        Returns:
            str: Sanitized text
        """
        if not text:
            return ""
        
        text = str(text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove JavaScript
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        
        # Remove event handlers
        text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        return text.strip()
