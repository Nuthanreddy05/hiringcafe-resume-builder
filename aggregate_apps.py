import os
import glob
import json

# Define paths
SOURCE_DIR = "/Users/nuthanreddyvaddireddy/Desktop/resume/software-enginner"
OUTPUT_FILE = "/Users/nuthanreddyvaddireddy/Desktop/CERTIFICATES/google/all_applications_data.json"

def main():
    if not os.path.exists(SOURCE_DIR):
        print(f"Error: Source directory {SOURCE_DIR} does not exist.")
        return

    applications = []
    
    # Get all job directories
    job_dirs = sorted([d for d in glob.glob(os.path.join(SOURCE_DIR, "*")) if os.path.isdir(d)])
    
    print(f"Found {len(job_dirs)} job folders.")

    for job_dir in job_dirs:
        app_data = {
            "folder_name": os.path.basename(job_dir),
            "jd": "",
            "resume": ""
        }
        
        # Read JD
        jd_path = os.path.join(job_dir, "JD.txt")
        if os.path.exists(jd_path):
            with open(jd_path, "r", errors="ignore") as f:
                app_data["jd"] = f.read()
                
        # Read Resume (LaTeX)
        resume_path = os.path.join(job_dir, "resume.tex")
        if os.path.exists(resume_path):
            with open(resume_path, "r", errors="ignore") as f:
                app_data["resume"] = f.read()
                
        applications.append(app_data)

    # Save to JSON in the workspace
    with open(OUTPUT_FILE, "w") as f:
        json.dump(applications, f, indent=2)
        
    print(f"Successfully aggregated {len(applications)} applications to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
