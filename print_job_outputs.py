import os
import glob

base_dir = "/Users/nuthanreddyvaddireddy/Desktop/resume/software-enginner"

def print_file_content(filepath, label):
    print(f"\n{'='*20} {label} {'='*20}")
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                print(content)
        else:
            print(f"File not found: {filepath}")
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    print('='*50)

def main():
    if not os.path.exists(base_dir):
        print(f"Directory not found: {base_dir}")
        return

    # Get all subdirectories
    subdirs = [d for d in glob.glob(os.path.join(base_dir, "*")) if os.path.isdir(d)]
    subdirs.sort()  # Sort to ensure consistent order

    print(f"Found {len(subdirs)} job folders in {base_dir}\n")

    for i, job_dir in enumerate(subdirs, 1):
        job_name = os.path.basename(job_dir)
        print(f"\n\n{'#'*80}")
        print(f"JOB {i}/{len(subdirs)}: {job_name}")
        print(f"{'#'*80}")

        jd_path = os.path.join(job_dir, "JD.txt")
        resume_path = os.path.join(job_dir, "resume.tex")

        print_file_content(jd_path, "JOB DESCRIPTION")
        print_file_content(resume_path, "GENERATED RESUME (LaTeX)")

if __name__ == "__main__":
    main()
