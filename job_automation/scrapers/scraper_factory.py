from typing import Dict, Type
from playwright.sync_api import BrowserContext
from job_automation.core.base_scraper import BaseScraper
from job_automation.scrapers.jobright_scraper import JobRightScraper

class ScraperFactory:
    """
    Factory to create scraper instances based on source name.
    """
    
    _scrapers: Dict[str, Type[BaseScraper]] = {
        'jobright': JobRightScraper,
        # 'hiringcafe': HiringCafeScraper, # To be implemented
    }
    
    @classmethod
    def create(cls, source: str, context: BrowserContext, config: dict = None) -> BaseScraper:
        """
        Create a scraper instance.
        """
        if source not in cls._scrapers:
            raise ValueError(f"Unknown source: {source}. Available: {list(cls._scrapers.keys())}")
        
        scraper_class = cls._scrapers[source]
        return scraper_class(context, config or {})
    
    @classmethod
    def register(cls, name: str, scraper_class: Type[BaseScraper]):
        """Register a new scraper dynamically."""
        cls._scrapers[name] = scraper_class
