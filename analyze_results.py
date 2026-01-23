import os
import json
import re
from pathlib import Path

# Path to Analysis
ROOT_DIR = Path("/Users/nuthanreddyvaddireddy/Desktop/Google Auto")

def analyze_folder(folder_path):
    issues = []
    score = 0
    status = "UNKNOWN"
    title = "Unknown"
    company = "Unknown"
    
    # 1. Read Score from Audit Log (Evaluation Report)
    audit_dir = folder_path / "_AUDIT"
    score_file = None
    
    # Try multiple naming conventions
    candidates = ["05_evaluation_report.md", "05_evaluation.md", "evaluation_report.md"]
    
    if audit_dir.exists():
        for c in candidates:
            p = audit_dir / c
            if p.exists():
                score_file = p
                break
                
    if score_file:
        text = score_file.read_text()
        # Look for "Score: 85" or similar
        m = re.search(r"Score:\s*(\d+)", text, re.IGNORECASE)
        if m:
            score = int(m.group(1))
    else:
        # Fallback: check if job is DONE (score likely > threshold)
        if "_DONE_" in folder_path.name:
            status = "DONE"
        else:
             status = "IN_PROGRESS"
    
    # 2. Check Resume Content (generated)
    tex_path = folder_path / "resume.tex"
    resume_text = ""
    if tex_path.exists():
        resume_text = tex_path.read_text().lower()
        
        # Fallback Score Check (Resume Comment)
        if score == 0:
            # Look for % Score: 85
            m_score = re.search(r"% Score:\s*(\d+)", tex_path.read_text())
            if m_score:
                score = int(m_score.group(1))

        # Check Soft Skills Presence
        
        # Check Soft Skills Presence
        soft_skills = ["communication", "team", "collaborat", "leader", "problem solv"]
        found_soft = [s for s in soft_skills if s in resume_text]
        if not found_soft:
            issues.append("Missing Common Soft Skills")
            
        # Check Negative Keywords in Resume (Sponsorship)
        if "sponsorship" in resume_text:
            # Context check: "requires sponsorship" vs "does not require"
            if "require sponsorship" in resume_text or "need sponsorship" in resume_text:
                issues.append("Resume mentions 'Need Sponsorship'")
                
    else:
        issues.append("Missing Resume.tex")

    # 3. Check Job Description (Source Quality)
    jd_path = folder_path / "job_description.txt"
    if jd_path.exists():
        jd_text = jd_path.read_text().lower()
        
        # Sponsorship Leak Check
        if "no sponsorship" in jd_text or "citizen only" in jd_text or "us citizen" in jd_text:
            issues.append("SPONSORSHIP LEAK (Job says No Sponsor)")
            
        # Industry Leak Check
        industries = ["natural gas", "petroleum", "biotech", "pharmaceutical"]
        found_ind = [i for i in industries if i in jd_text]
        if found_ind:
            issues.append(f"INDUSTRY LEAK ({', '.join(found_ind)})")
            
    return {
        "folder": folder_path.name,
        "company": company,
        "score": score,
        "issues": issues
    }

def main():
    results = []
    folders = [f for f in ROOT_DIR.iterdir() if f.is_dir() and not f.name.startswith("_")]
    
    print(f"Analyzing {len(folders)} folders...")
    
    for folder in folders:
        res = analyze_folder(folder)
        results.append(res)
        
    # Generate Report
    print("\n" + "="*60)
    print(f"ANALYSIS REPORT ({len(folders)} Jobs)")
    print("="*60)
    
    avg_score = sum(r['score'] for r in results) / len(results) if results else 0
    print(f"Average Score: {avg_score:.1f}/100")
    
    leaks = [r for r in results if any("LEAK" in i for i in r['issues'])]
    print(f"Bad Jobs Found (Leaks): {len(leaks)}")
    
    if leaks:
        print("\n--- LEAKED JOBS (Should stem from old filter) ---")
        for l in leaks:
            print(f"[{l['company']}] {l['folder']}: {l['issues']}")
            
    # Soft Skill Check
    missing_soft = [r for r in results if "Missing Common Soft Skills" in r['issues']]
    print(f"\nResumes Missing Soft Skills: {len(missing_soft)}")
    
    # Save formatted report
    report_path = Path("analysis_report.md")
    with open(report_path, "w") as f:
        f.write(f"# 📊 100-Job Quality Analysis\n\n")
        f.write(f"**Total Jobs:** {len(folders)}\n")
        f.write(f"**Average Score:** {avg_score:.1f}\n")
        f.write(f"**Bad Job Leaks:** {len(leaks)}\n\n")
        
        f.write("## ⚠️ Flagged Issues\n")
        for r in results:
            if r['issues']:
                f.write(f"- **{r['company']}**: {', '.join(r['issues'])}\n")

if __name__ == "__main__":
    main()
