import os
import sys
from pathlib import Path

# Add current dir to path to import local module
sys.path.append(str(Path.cwd()))

try:
    from job_auto_apply_internet import should_skip_job, check_sponsorship_viability, clean_jd_smart, Job
except ImportError:
    print("❌ Could not import job_auto_apply_internet. Make sure you are in the correct directory.")
    sys.exit(1)

ROOT_DIR = Path("/Users/nuthanreddyvaddireddy/Desktop/Google Auto")

def retro_test():
    print(f"🔍 Retro-Analyzing jobs in {ROOT_DIR} with NEW Logic...\n")
    
    folders = [f for f in ROOT_DIR.iterdir() if f.is_dir() and not f.name.startswith("_")]
    processed = 0
    would_skip = 0
    reasons = {}

    print(f"{'STATUS':<10} | {'REASON':<40} | {'COMPANY'}")
    print("-" * 80)

    for folder in folders:
        jd_path = folder.joinpath("JD.txt")
        if not jd_path.exists():
            # Try alternate name if needed
            jd_path = folder.joinpath("job_description.txt")
            if not jd_path.exists():
                continue
            
        text = jd_path.read_text(errors='ignore')
        
        # 1. Source Filter Check
        # We dummy the title as 'Unknown' since we might not have it easily, 
        # but usually the folder name has company.
        skip, reason = should_skip_job("Unknown Title", text)
        
        # 2. Process Filter Check (Sponsorship)
        # Note: check_sponsorship_viability returns False if it FAILS (i.e. we should skip)
        is_viable = check_sponsorship_viability(text)
        
        status = "KEEP"
        fail_reason = ""
        
        if skip:
            status = "SKIP"
            fail_reason = reason
        elif not is_viable:
            status = "SKIP"
            fail_reason = "Sponsorship Viability Failed"
            
        if status == "SKIP":
            would_skip += 1
            print(f"{'⛔ SKIP':<10} | {fail_reason:<40} | {folder.name}")
            reasons[fail_reason] = reasons.get(fail_reason, 0) + 1
        
        processed += 1

    print("\n" + "=" * 60)
    print("📊 RETRO ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Total Jobs Analyzed: {processed}")
    print(f"Would be SKIPPED now: {would_skip}")
    print(f"Retention Rate:      {((processed - would_skip)/processed)*100:.1f}%")
    print("\nReasons for Skipping:")
    for r, count in reasons.items():
        print(f"  - {r}: {count}")

if __name__ == "__main__":
    retro_test()
