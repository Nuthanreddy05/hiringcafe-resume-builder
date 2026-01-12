import argparse
import sys
import time
from database import JobManager

def main():
    parser = argparse.ArgumentParser(description="Load jobs into the batch system.")
    parser.add_argument("--url", help="Single Job URL to add")
    parser.add_argument("--company", help="Company Name", default="Unknown")
    parser.add_argument("--file", help="File containing URLs (one per line)")
    parser.add_argument("--source", help="Source tag (e.g. hiringcafe)", default="manual")
    
    args = parser.parse_args()
    db = JobManager()

    if args.url:
        print(f"Adding single job: {args.url}")
        db.add_job(f"{args.source}_{len(db.get_pending_jobs()) + 100}", args.url, args.company)
        print("✅ Added.")
        
    elif args.file:
        print(f"Loading from {args.file}...")
        try:
            with open(args.file, 'r') as f:
                count = 0
                for line in f:
                    url = line.strip()
                    if url and url.startswith("http"):
                        count += 1
                        # Use timestamp or random to avoid ID collision if stats fails
                        job_id = f"{args.source}_{int(time.time())}_{count}"
                        db.add_job(job_id, url, args.company)
                        print(f"  + Added: {url}")
            print(f"✅ Loaded {count} jobs.")
        except Exception as e:
            print(f"❌ Error reading file: {e}")
    else:
        # Interactive mode
        print("Enter Job URLs (one per line). Press Ctrl+D (or Ctrl+Z on Windows) to finish:")
        lines = sys.stdin.readlines()
        count = 0
        for line in lines:
            url = line.strip()
            if url and url.startswith("http"):
                count += 1
                job_id = f"{args.source}_{int(time.time())}_{count}"
                db.add_job(job_id, url, args.company)
        print(f"✅ Loaded {count} jobs.")

if __name__ == "__main__":
    main()
