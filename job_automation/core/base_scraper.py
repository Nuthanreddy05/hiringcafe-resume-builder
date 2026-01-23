from abc import ABC, abstractmethod
from typing import List, Optional
from playwright.sync_api import BrowserContext
from .models import Job

class BaseScraper(ABC):
    """
    Abstract base class for all job scrapers.
    Enforces a consistent interface for collecting links and details.
    """
    
    def __init__(self, context: BrowserContext, config: dict):
        self.context = context
        self.config = config
        self.jobs_scraped = 0
        self.jobs_skipped = 0
        self.jobs_failed = 0
    
    @abstractmethod
    def collect_job_links(self, start_url: str, max_jobs: int) -> List[str]:
        """
        Collect job listing URLs from the search page.
        Must be implemented by child classes.
        """
        pass
    
    @abstractmethod
    def fetch_job_details(self, job_url: str) -> Optional[Job]:
        """
        Fetch full job details from a specific job URL.
        Must be implemented by child classes.
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """
        Return the unique name of the job source (e.g., 'hiringcafe', 'jobright').
        """
        pass
    
    def scrape_jobs(self, start_url: str, max_jobs: int) -> List[Job]:
        """
        Main workflow method (Template Pattern).
        Orchestrates the scraping process using the implemented abstract methods.
        """
        print(f"\n{'='*80}")
        print(f"🚀 Starting {self.get_source_name().upper()} scraper")
        print(f"{'='*80}")
        
        # Step 1: Collect links
        print(f"📋 Collecting job links from {start_url[:50]}...")
        job_links = self.collect_job_links(start_url, max_jobs)
        print(f"✓ Found {len(job_links)} job links to process")
        
        # Step 2: Fetch details
        jobs: List[Job] = []
        for idx, link in enumerate(job_links, 1):
            print(f"\n🔍 PROCESSING JOB [{idx}/{len(job_links)}]")
            try:
                job = self.fetch_job_details(link)
                if job:
                    # Enforce source name
                    job.source = self.get_source_name()
                    jobs.append(job)
                    self.jobs_scraped += 1
                else:
                    self.jobs_skipped += 1
            except Exception as e:
                print(f"❌ Critical error processing {link}: {e}")
                self.jobs_failed += 1
        
        self._print_summary()
        return jobs
    
    def _print_summary(self):
        """Print final scraping statistics"""
        print(f"\n{'='*80}")
        print(f"📊 {self.get_source_name().upper()} SCRAPING SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Successfully Scraped: {self.jobs_scraped}")
        print(f"⊗ Skipped/Invalid:     {self.jobs_skipped}")
        print(f"✗ Failed:              {self.jobs_failed}")
        print(f"{'='*80}")
