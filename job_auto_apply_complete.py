#!/usr/bin/env python3
"""
COMPLETE AUTO-APPLY PIPELINE
Scrapes → Generates Resumes → Auto-Applies in ONE COMMAND

Usage:
    # Safe Mode (Pause for review before each submit)
    python job_auto_apply_complete.py --max_jobs 5
    
    # Auto-Submit Mode (RISKY - submits everything automatically)
    python job_auto_apply_complete.py --max_jobs 20 --submit
    
    # Custom output folder
    python job_auto_apply_complete.py --max_jobs 10 --output "Fresh_Jobs_Feb_3"
"""

import argparse
import json
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# We'll use subprocess to call the existing scripts instead of importing
try:
    from job_auto_submit import process_job, identify_ats
    from playwright.sync_api import sync_playwright
except ImportError:
    print("⚠️  Missing dependencies. Install with:")
    print("   pip install playwright")
    print("   playwright install chromium")
    sys.exit(1)


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_OUTPUT_DIR = "Google Auto Internet"
PROFILE_PATH = "profile.json"


# ============================================================================
# Helper Functions
# ============================================================================

def load_profile() -> Dict[str, Any]:
    """Load user profile from JSON"""
    if not Path(PROFILE_PATH).exists():
        print(f"❌ Profile file not found: {PROFILE_PATH}")
        print("   Create profile.json with your information!")
        sys.exit(1)
    
    return json.loads(Path(PROFILE_PATH).read_text())


def find_job_folders(output_dir: str) -> List[Path]:
    """Find all job folders in output directory"""
    output_path = Path(output_dir)
    if not output_path.exists():
        return []
    
    # Find folders with resumes
    folders = []
    for folder in output_path.iterdir():
        if folder.is_dir():
            resume = folder / "NuthanReddy.pdf"
            apply_url = folder / "apply_url.txt"
            if resume.exists() and apply_url.exists():
                folders.append(folder)
    
    return folders


def categorize_jobs_by_platform(folders: List[Path]) -> Dict[str, List[Path]]:
    """Categorize jobs by ATS platform"""
    categorized = {
        "greenhouse": [],
        "lever": [],
        "workday": [],
        "taleo": [],
        "custom": [],
        "unknown": []
    }
    
    for folder in folders:
        url_file = folder / "apply_url.txt"
        url = url_file.read_text().strip()
        platform = identify_ats(url)
        
        categorized[platform].append(folder)
    
    return categorized


# =============================================================================
# Main Pipeline
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Complete Auto-Apply Pipeline: Scrape → Generate → Apply"
    )
    parser.add_argument(
        "--max_jobs", 
        type=int, 
        default=10,
        help="Maximum number of jobs to process (default: 10)"
    )
    parser.add_argument(
        "--submit", 
        action="store_true",
        help="Auto-submit applications (RISKY! Default is pause for review)"
    )
    parser.add_argument(
        "--output", 
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for job folders (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--skip_scrape", 
        action="store_true",
        help="Skip scraping, only apply to existing job folders"
    )
    parser.add_argument(
        "--platforms",
        nargs="+",
        default=["greenhouse", "lever", "workday", "taleo", "custom"],
        help="Platforms to auto-apply to (default: greenhouse lever workday taleo custom)"
    )
    
    args = parser.parse_args()
    
    # Banner
    print("="*70)
    print("🚀 COMPLETE AUTO-APPLY PIPELINE")
    print("="*70)
    print(f"📊 Max Jobs: {args.max_jobs}")
    print(f"📁 Output: {args.output}")
    print(f"🎯 Platforms: {', '.join(args.platforms)}")
    print(f"⚡ Submit Mode: {'AUTO-SUBMIT (RISKY)' if args.submit else 'SAFE (Manual Review)'}")
    print("="*70)
    
    # Load profile
    print("\n📋 Loading profile...")
    profile = load_profile()
    print(f"   ✅ Profile loaded: {profile['first_name']} {profile['last_name']}")
    
    # STEP 1-2: Scrape + Generate Resumes
    if not args.skip_scrape:
        print("\n" + "="*70)
        print("📥 STEP 1-2: SCRAPING JOBS & GENERATING RESUMES")
        print("="*70)
        
        # Use the default HiringCafe URL from the existing script
        hiringcafe_url = 'https://hiring.cafe/?searchState=%7B%22dateFetchedPastNDays%22%3A2%2C%22sortBy%22%3A%22date%22%2C%22jobTitleQuery%22%3A%22%28%5C%22software+engineer%5C%22+OR+%5C%22software+developer%5C%22+OR+%5C%22software+development+engineer%5C%22+OR+%5C%22backend+engineer%5C%22+OR+%5C%22frontend+engineer%5C%22+OR+%5C%22front+end+engineer%5C%22+OR+%5C%22full+stack+engineer%5C%22+OR+%5C%22devops+engineer%5C%22++OR+%5C%22data+scientist%5C%22+OR+%5C%22data+engineer%5C%22+OR+%5C%22machine+learning+engineer%5C%22+OR+%5C%22ml+engineer%5C%22+OR+%5C%22ai+engineer%5C%22%29%22%2C%22securityClearances%22%3A%5B%22None%22%2C%22Other%22%5D%2C%22roleYoeRange%22%3A%5B0%2C4%5D%2C%22seniorityLevel%22%3A%5B%22No+Prior+Experience+Required%22%2C%22Entry+Level%22%2C%22Mid+Level%22%5D%2C%22commitmentTypes%22%3A%5B%22Full+Time%22%2C%22Part+Time%22%2C%22Contract%22%2C%22Temporary%22%2C%22Seasonal%22%2C%22Volunteer%22%5D%2C%22departments%22%3A%5B%22Engineering%22%2C%22Software+Development%22%2C%22Information+Technology%22%2C%22Data+and+Analytics%22%5D%2C%22usaGovPref%22%3A%22exclude%22%2C%22excludedIndustries%22%3A%5B%22educational+organizations%22%5D%2C%22isNonProfit%22%3A%22forprofit%22%2C%22roleTypes%22%3A%5B%22Individual+Contributor%22%5D%7D'
        
        print(f"🔍 Scraping up to {args.max_jobs} jobs from HiringCafe...")
        print("⏳ This may take 10-30 minutes depending on job count...")
        
        try:
            # Call existing script via subprocess
            cmd = [
                "python3", "job_auto_apply_internet.py",
                "--start_url", hiringcafe_url,
                "--max_jobs", str(args.max_jobs),
                "--headless",
                "--out_dir", args.output
            ]
           
            print(f"\n📝 Running command:")
            print(f"   {' '.join(cmd)}\n")
            
            result = subprocess.run(cmd, check=True, capture_output=False)
            
            if result.returncode != 0:
                print(f"❌ Scraping failed with code {result.returncode}")
                sys.exit(1)
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Error in scraping/resume generation: {e}")
            print("   Check logs for details.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            sys.exit(1)
    else:
        print("\n⏭️  Skipping scrape (--skip_scrape flag set)")
    
    # Find all job folders
    print(f"\n🔍 Finding job folders in {args.output}...")
    job_folders = find_job_folders(args.output)
    
    if not job_folders:
        print(f"❌ No job folders found in {args.output}")
        print("   Make sure folders contain NuthanReddy.pdf and apply_url.txt")
        sys.exit(1)
    
    print(f"   ✅ Found {len(job_folders)} job folders")
    
    # Categorize by platform
    categorized = categorize_jobs_by_platform(job_folders)
    
    print("\n📊 Platform Breakdown:")
    for platform, folders in categorized.items():
        print(f"   - {platform.upper()}: {len(folders)} jobs")
    
    # Filter by selected platforms
    jobs_to_apply = []
    for platform in args.platforms:
        jobs_to_apply.extend(categorized.get(platform, []))
    
    print(f"\n🎯 Applying to {len(jobs_to_apply)} jobs on selected platforms")
    
    if categorized["unknown"]:
        print(f"   ⚠️  {len(categorized['unknown'])} jobs on unsupported platforms (skipped)")
    
    # STEP 3: Auto-Apply
    if jobs_to_apply:
        print("\n" + "="*70)
        print("🚀 STEP 3: AUTO-APPLYING TO JOBS")
        print("="*70)
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            
            for i, folder in enumerate(jobs_to_apply, 1):
                print(f"\n{'='*70}")
                print(f"[{i}/{len(jobs_to_apply)}] Processing: {folder.name}")
                print(f"{'='*70}")
                
                try:
                    status = process_job(
                        job_dir=folder,
                        profile=profile,
                        context=context,
                        headless=False,
                        submit=args.submit
                    )
                    
                    if status in ["Submitted", "Submitted (Automated)"]:
                        success_count += 1
                        # Rename folder to mark as applied
                        new_name = f"[APPLIED]_{folder.name}"
                        if not (folder.parent / new_name).exists():
                            folder.rename(folder.parent / new_name)
                    
                    elif status in ["Ready for Review", "Paused for Manual Review (Hybrid)"]:
                        print("\n   ⏸️  PAUSED FOR MANUAL REVIEW")
                        print("   👉 Check the browser window")
                        print("   👉 Verify all fields are filled correctly")
                        print("   👉 Submit manually if everything looks good")
                        
                        choice = input("\n   Did you submit? (y/n/skip): ").lower()
                        
                        if choice == 'y':
                            success_count += 1
                            new_name = f"[DONE]_{folder.name}"
                            if not (folder.parent / new_name).exists():
                                folder.rename(folder.parent / new_name)
                        elif choice == 'skip':
                            skipped_count += 1
                        else:
                            failed_count += 1
                            new_name = f"[REVIEW]_{folder.name}"
                            if not (folder.parent / new_name).exists():
                                folder.rename(folder.parent / new_name)
                    
                    else:
                        failed_count += 1
                        print(f"   ⚠️  Status: {status}")
                
                except KeyboardInterrupt:
                    print("\n\n⚠️  Process interrupted by user")
                    break
                
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    failed_count += 1
                    # Rename to mark as failed
                    new_name = f"[FAILED]_{folder.name}"
                    if not (folder.parent / new_name).exists():
                        folder.rename(folder.parent / new_name)
            
            browser.close()
        
        # Final Report
        print("\n" + "="*70)
        print("✅ PIPELINE COMPLETE!")
        print("="*70)
        print(f"📊 Total Jobs Processed: {len(jobs_to_apply)}")
        print(f"   ✅ Successfully Applied: {success_count}")
        print(f"   ❌ Failed/Review Needed: {failed_count}")
        print(f"   ⏭️  Skipped: {skipped_count}")
        
        # Time estimation
        est_time = len(jobs_to_apply) * 2  # 2 minutes per job
        print(f"\n⏱️  Time Saved vs Manual: ~{len(jobs_to_apply) * 15 - est_time} minutes")
        print("   (Manual: ~15 min/job, Automated: ~2 min/job)")
        
        # Next steps
        if categorized["unknown"]:
            print(f"\n💡 Next Steps:")
            print(f"   - Review {len(categorized['unknown'])} unsupported platform jobs manually")
            print(f"   - Check folders marked [FAILED] or [REVIEW]")
        
        print("\n" + "="*70)
    
    else:
        print("\n⚠️  No jobs to apply to on selected platforms")


if __name__ == "__main__":
    main()
