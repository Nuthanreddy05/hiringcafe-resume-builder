#!/usr/bin/env python3
"""
Job Aggregator - The "Mega-Scraper"
Uses python-jobspy to scrape LinkedIn, Indeed, Glassdoor, and ZipRecruiter simultaneously.
"""

import csv
import json
import logging
import os
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from jobspy import scrape_jobs

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def run_aggregator(
    search_term: str,
    location: str,
    results_wanted: int = 20,
    output_file: str = "internet_jobs/jobs.csv"
):
    """
    Scrape jobs from multiple sites and save to CSV.
    """
    # Create output directory
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    logger.info(f"🚀 Starting Multi-Site Scraper for: '{search_term}' in '{location}'")
    
    # sites = ["indeed", "linkedin", "glassdoor", "zip_recruiter", "google"]
    # Limiting sites for stability if needed, but trying all for maximum reach
    sites = ["linkedin", "indeed", "glassdoor", "zip_recruiter", "google"]

    logger.info(f"   Targeting sites: {', '.join(sites)}")
    
    try:
        jobs = scrape_jobs(
            site_name=sites,
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=72,  # Only fresh jobs (last 3 days)
            country_indeed='USA',
            
            # rate_limit/proxy options could be added here if needed
            # linkedin_fetch_description=True # This is slower but gets full desc.
            # We might want to fetch description later ONLY for filtered jobs to save time/ban-risk,
            # BUT JobSpy does it well in batch. Let's try getting it now.
        )
        
        logger.info(f"   ✅ Scraped {len(jobs)} jobs")
        
        # Save to CSV
        jobs.to_csv(output_file, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)
        logger.info(f"   💾 Saved raw results to {output_file}")
        
        return output_file
        
    except Exception as e:
        logger.error(f"   ❌ Scraping failed: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape jobs from the entire internet")
    parser.add_argument("--term", default="Software Engineer", help="Job title/search term")
    parser.add_argument("--location", default="United States", help="Location")
    parser.add_argument("--count", type=int, default=20, help="Number of jobs per site to fetch")
    
    args = parser.parse_args()
    
    run_aggregator(
        search_term=args.term,
        location=args.location,
        results_wanted=args.count
    )
