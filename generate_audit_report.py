import os
import json
from pathlib import Path
import datetime

OUTPUT_DIR = Path("/Users/nuthanreddyvaddireddy/Desktop/Google Auto")
REPORT_FILE = Path("/Users/nuthanreddyvaddireddy/Desktop/Google Auto/audit_package_batch_10.md")

PROMPTS_FILE = Path("/Users/nuthanreddyvaddireddy/Desktop/CERTIFICATES/google/job_auto_apply_internet.py")
RESUME_PROMPT_FILE = Path("/Users/nuthanreddyvaddireddy/Desktop/CERTIFICATES/google/resume_json_prompt.txt")

def generate_report():
    print(f"Scanning {OUTPUT_DIR}...")
    
    if not OUTPUT_DIR.exists():
        print(f"Directory not found: {OUTPUT_DIR}")
        return

    dirs = [d for d in OUTPUT_DIR.iterdir() if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".")]
    # Sort by creation time usually, or name
    dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    report = []
    report.append(f"# 📊 Audit Package: Batch 10 Jobs")
    report.append(f"Generated at: {datetime.datetime.now().isoformat()}")
    report.append(f"Total Folders Found: {len(dirs)}")
    report.append("\n---\n")

    # 1. System Prompts
    report.append("## 🤖 System Prompts (Snapshot)\n")
    
    # DeepSeek Prompt
    try:
        ds_prompt = RESUME_PROMPT_FILE.read_text(encoding="utf-8")
        report.append("### DeepSeek System Prompt\n```text\n" + ds_prompt + "\n```\n")
    except Exception as e:
        report.append(f"Could not read DeepSeek prompt: {e}\n")

    # Gemini Prompt (Extracted from Python)
    try:
        py_code = PROMPTS_FILE.read_text(encoding="utf-8")
        start = py_code.find('prompt = f"""')
        if start != -1:
            end = py_code.find('"""', start + 15)
            gemini_prompt = py_code[start:end+3]
            report.append("### Gemini Evaluator Prompt\n```python\n" + gemini_prompt + "\n```\n")
        else:
            report.append("Could not extract Gemini prompt from python file.\n")
    except Exception as e:
        report.append(f"Could not read Python file: {e}\n")
    
    report.append("\n---\n")

    # 2. Iterate Jobs
    report.append("## 📂 Job Details\n")
    
    limit = 10
    count = 0
    
    for job_dir in dirs:
        if count >= limit: break
        
        meta_path = job_dir / "meta.json"
        resume_path = job_dir / "resume.tex"
        iterations_path = job_dir / "iterations.json"
        jd_path = job_dir / "JD.txt"
        
        if not meta_path.exists():
            continue
            
        count += 1
        
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8', errors='ignore'))
        except:
            meta = {"title": "Error reading meta", "company": "Unknown"}

        title = meta.get("title", "Unknown Title")
        company = meta.get("company", "Unknown Company")
        score = meta.get("best_score", 0)
        iterations = meta.get("total_iterations", 0)
        
        report.append(f"### Job {count}: {title} @ {company}")
        report.append(f"**Path**: `{job_dir.name}`")
        report.append(f"**Score**: {score}/100")
        report.append(f"**Iterations**: {iterations}")
        report.append(f"**Status**: {'✅ PASSED' if score >= 80 else '❌ FAILED/ITERATING'}")
        
        # Link to JD
        if jd_path.exists():
            jd_preview = jd_path.read_text(encoding='utf-8', errors='ignore')[:500].replace("\n", " ") + "..."
            report.append(f"\n**Job Description (Snippet)**:\n> {jd_preview}\n")
        
        # Evaluations
        if iterations_path.exists():
            try:
                its = json.loads(iterations_path.read_text(encoding='utf-8', errors='ignore'))
                report.append(f"\n**Evaluations ({len(its)} iterations)**:")
                for it in its:
                    report.append(f"- **Iter {it.get('iteration')}** (Score: {it.get('score')}):")
                    feedback = it.get('feedback', 'No feedback').replace('\n', '\n  > ')
                    report.append(f"  > {feedback}\n")
            except:
                report.append("Error reading evaluations.\n")
        
        # Resume Content
        if resume_path.exists():
            resume_content = resume_path.read_text(encoding='utf-8', errors='ignore')
            report.append(f"\n**Generated Resume (LaTeX)**:\n```latex\n{resume_content}\n```\n")
        
        report.append("\n---\n")

    REPORT_FILE.write_text("\n".join(report), encoding="utf-8")
    print(f"✅ Report generated at {REPORT_FILE}")

if __name__ == "__main__":
    generate_report()
