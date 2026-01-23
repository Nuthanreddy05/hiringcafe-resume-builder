
import sys
import os
import json
from pathlib import Path
from dataclasses import dataclass

sys.path.append(os.getcwd())

from job_automation.core.llm_client import LLMClient
from job_automation.core.resume_generator import ResumeGenerator
from job_automation.core.models import Job

def debug_optimization():
    # Setup
    target_dir = Path("/Users/nuthanreddyvaddireddy/Desktop/Google Auto/Unknown - BI Analyst Senior Intermediate")
    if not target_dir.exists():
        print(f"❌ Folder not found: {target_dir}")
        return

    print(f"🔍 Debugging Optimization for: {target_dir.name}")
    
    # Load Data
    try:
        if (target_dir / "details.json").exists():
            details = json.loads((target_dir / "details.json").read_text())
            job = Job(**details)
        else:
            print("⚠️ details.json missing. Inferring from folder name.")
            parts = target_dir.name.split(" - ", 1)
            company = parts[0]
            title = parts[1] if len(parts) > 1 else "Unknown Role"
            # We need description. loaded from clean_jd is fine for generation?
            # actually clean_jd is the CLEANED one. We need RAW?
            # ResumeGenerator.generate_resume takes clean_jd. So we are good.
            # But the Job object is used for title/company.
            job = Job(title=title, company=company, url="http://debug.url", description="Start from clean_jd")
            
        clean_jd = (target_dir / "clean_jd.txt").read_text()
        base_resume_path = Path("profile.json")
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        return

    # Initialize Generator
    llm = LLMClient()
    generator = ResumeGenerator(llm, Path("debug_output"), base_resume_path)
    
    # 1. Generate Fresh V1
    print("\n--- Generating V1 Resume ---")
    resume_v1 = generator.generate_resume(job, clean_jd)
    
    # 2. Evaluate V1
    print("\n--- Evaluating V1 ---")
    score_v1, eval_text_v1, approved_v1 = generator.evaluate_resume_debug(job, clean_jd, resume_v1)
    print(f"📊 V1 Score: {score_v1}")
    
    if score_v1 >= 85:
        print("✅ V1 is already good! (>=85)")
        print(json.dumps(resume_v1, indent=2))
        return

    # 3. Optimize to V2
    print("\n--- Optimizing to V2 ---")
    feedback = eval_text_v1 # Contains the JSON feedback
    resume_v2 = generator.optimize_resume(job, clean_jd, resume_v1, feedback)
    
    # 4. Evaluate V2
    print("\n--- Evaluating V2 ---")
    score_v2, eval_text_v2, approved_v2 = generator.evaluate_resume_debug(job, clean_jd, resume_v2)
    print(f"📊 V2 Score: {score_v2}")
    
    # Compare
    print("\n--- Comparison ---")
    print(f"V1 -> V2: {score_v1} -> {score_v2}")
    
    if score_v2 < score_v1:
        print("⚠️  SCORE DECREASE DETECTED!")
        print("FEEDBACK GIVEN:")
        print(feedback[:1000] + "...")
        print("\nCHANGES MADE (Approx):")
        # Simple diff of specific fields
        # ... (Diff logic)

    # Save outputs for inspection
    (target_dir / "debug_v1.json").write_text(json.dumps(resume_v1, indent=2))
    (target_dir / "debug_v2.json").write_text(json.dumps(resume_v2, indent=2))
    (target_dir / "debug_feedback.json").write_text(feedback)
    print(f"\nSaved debug files to {target_dir}")

# Monkey patch evaluate_resume to return details
def evaluate_resume_debug(self, job, clean_jd, resume_json):
    if not self.evaluator_prompt_path.exists():
        return 0, "No Prompt", False
    eval_prompt_template = self.evaluator_prompt_path.read_text(encoding="utf-8")
    resume_str = json.dumps(resume_json, indent=2)
    final_prompt = f"{eval_prompt_template}\nJOB DESCRIPTION:\n{clean_jd}\nGENERATED RESUME JSON:\n{resume_str}"
    print("   (Calling Gemini for Eval...)")
    evaluation = self.llm.generate_json("gemini", final_prompt, temperature=0.2)
    
    score = evaluation.get("overall_score") or evaluation.get("score") or 0
    if isinstance(score, str) and "/" in score: score = int(score.split("/")[0])
    return int(score), json.dumps(evaluation, indent=2), int(score)>=85

ResumeGenerator.evaluate_resume_debug = evaluate_resume_debug

if __name__ == "__main__":
    debug_optimization()
