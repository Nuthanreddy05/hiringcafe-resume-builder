from dataclasses import dataclass, field
from typing import List, Optional, Dict
import datetime

@dataclass
class Job:
    """
    Represents a single job posting regardless of source.
    """
    url: str
    title: str
    company: str
    description: str
    location: str = "Unknown"
    posted_date: Optional[datetime.datetime] = None
    source: str = "unknown"  # 'hiringcafe', 'jobright', etc.
    posted_at: str = "" # e.g. "3 hours ago"
    apply_url: Optional[str] = None
    
    # Metadata for processing
    id: str = field(default_factory=lambda: "")  # Unique ID (e.g., from URL hash)
    is_valid: bool = True
    rejection_reason: Optional[str] = None
    
    # Content analysis
    technical_skills: List[str] = field(default_factory=list)
    soft_skills: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    # Resume generation status
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    score: int = 0
    feedback: str = ""

@dataclass
class ScrapingConfig:
    """
    Configuration for a scraping run.
    """
    start_url: str
    max_jobs: int
    headless: bool
    output_dir: str
    resume_prompt_file: str
    evaluator_prompt_file: str
    approval_threshold: int = 80
