import os
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
import time

from job_automation.core.models import Job
from job_automation.core.llm_client import LLMClient
from job_automation.utils.text_utils import clean_description, trim_jd_smart, clean_jd_smart, check_sponsorship_viability

class ResumeGenerator:
    """
    Orchestrates the resume generation process:
    1. JD Cleaning (DeepSeek)
    2. Relevance Check (DeepSeek)
    3. Resume Writing (DeepSeek)
    4. Evaluation (Gemini)
    5. Optimization Loop
    """
    
    def __init__(self, llm_client: LLMClient, output_dir: Path, base_resume_path: Path, writer_prompt_path: Optional[Path] = None, evaluator_prompt_path: Optional[Path] = None, iteration_prompt_path: Optional[Path] = None):
        self.llm = llm_client
        self.output_dir = output_dir
        self.base_resume_path = base_resume_path
        
        # Load Prompts (Assuming they are in the root directory relative to execution context, 
        # or we could make this configurable. For now, hardcoding based on user's setup)
        self.root_dir = Path(os.getcwd())
        
        # Default to HiringCafe Legacy (Single Source of Truth) if not overridden
        if writer_prompt_path:
             self.writer_prompt_path = writer_prompt_path
             print(f"      📝 Using Specialized Writer Prompt: {writer_prompt_path.absolute()}")
        else:
             self.writer_prompt_path = self.root_dir / "HiringCafe_Resume_Builder/resume_json_prompt.txt"

        if evaluator_prompt_path:
             self.evaluator_prompt_path = evaluator_prompt_path
             print(f"      ⚖️  Using Specialized Evaluator Prompt: {evaluator_prompt_path.absolute()}")
        else:
             self.evaluator_prompt_path = self.root_dir / "resume_evaluator_prompt_v3.txt"
             
        # Iteration Prompt (JobRight support)
        if iteration_prompt_path:
            self.iteration_prompt_path = iteration_prompt_path
            print(f"      🔄 Using Specialized Iteration Prompt: {iteration_prompt_path.absolute()}")
        else:
            self.iteration_prompt_path = None

        self.clean_jd_path = self.root_dir / "prompts/clean_jd.txt"
        self.relevance_path = self.root_dir / "prompts/relevance_check.txt"
        
        # Load Base Resume JSON
        try:
            self.base_resume_json = json.dumps(json.loads(base_resume_path.read_text()), indent=2)
        except Exception as e:
            print(f"❌ Failed to load base resume from {base_resume_path}: {e}")
            self.base_resume_json = "{}"

    def clean_jd(self, jd_text: str) -> str:
        """Layer 1: Clean and restructure JD using DeepSeek."""
        if not self.clean_jd_path.exists():
             # Fallback if file missing
             clean_prompt = f"Clean this JD:\n{jd_text}"
        else:
             template = self.clean_jd_path.read_text(encoding="utf-8")
             clean_prompt = template.replace("{jd_text}", jd_text)

        return self.llm.generate_text("deepseek", clean_prompt, temperature=0.1)

    def check_relevance(self, clean_jd: str) -> Dict[str, Any]:
        """Layer 2: Check if job is relevant (Software/Data) and allows sponsorship."""
        if not self.relevance_path.exists():
            # Fallback
            prompt = f"Check relevance:\n{clean_jd}"
        else:
            template = self.relevance_path.read_text(encoding="utf-8")
            prompt = template.replace("{clean_jd}", clean_jd)

        return self.llm.generate_json("deepseek", prompt, temperature=0.1)

    def _build_writer_prompt(self, job: Job, clean_jd: str, current_resume: Optional[Dict] = None, feedback: Optional[str] = None) -> str:
        """Construct the writer prompt, handling iteration feedback like legacy code."""
        if not self.writer_prompt_path.exists():
            raise FileNotFoundError(f"Writer prompt not found at {self.writer_prompt_path}")
            
        base_instruction = self.writer_prompt_path.read_text(encoding="utf-8")
        
        # [Legacy Logic] Calculate Soft Skills Ratio
        soft_skills = ["communication", "collaboration", "teamwork", "leadership", "mentoring", "ownership", "problem-solving"]
        soft_count = sum(1 for s in soft_skills if s in clean_jd.lower())
        total_words = len(clean_jd.split())
        soft_ratio = str(round(soft_count / (total_words * 0.05 + 1), 2))
        
        # If feedback exists, append it to the instruction block
        if feedback and current_resume:
            if self.iteration_prompt_path and self.iteration_prompt_path.exists():
                # Use External Template
                template = self.iteration_prompt_path.read_text(encoding="utf-8")
                suffix = template.replace("{current_resume_json}", json.dumps(current_resume, indent=2))
                suffix = suffix.replace("{feedback}", feedback)
                base_instruction += suffix
            else:
                # Legacy Hardcoded Logic
                base_instruction += f"""

--- PREVIOUS DRAFT JSON (EDIT THIS) ---
{json.dumps(current_resume, indent=2)}

--- CRITICAL FEEDBACK FROM LAST ITERATION ---
{feedback}

INSTRUCTION: Refine the PREVIOUS DRAFT based on feedback. Do not start from scratch if the previous content was good. Return ONLY valid JSON.
"""

        # Construct Full Context
        base_resume_str = self.base_resume_path.read_text(encoding="utf-8")
        
        prompt = f"""{base_instruction}

JOB INFORMATION:
Title: {job.title}
Company: {job.company}
Soft Skills Ratio: {soft_ratio} (>0.1 suggests higher weight)

JOB DESCRIPTION (trimmed):
{clean_jd}

BASE RESUME JSON:
{base_resume_str}

### v17.0 STRATEGIC BLUEPRINT (EXECUTE THIS):
No Strategy Provided.
"""
        return prompt

    def generate_resume(self, job: Job, clean_jd: str) -> Dict[str, Any]:
        """Generate first draft resume."""
        print(f"      ✍️  Generating resume for {job.title}...")
        
        final_prompt = self._build_writer_prompt(job, clean_jd)
        
        try:
            resume_json = self.llm.generate_json("deepseek", final_prompt, temperature=0.7)
            return resume_json
        except Exception as e:
            print(f"      ❌ Generation error: {e}")
            return {}

    def evaluate_resume(self, job: Job, clean_jd: str, resume_json: Dict) -> Dict[str, Any]:
        """
        Evaluate using Gemini.
        """
        if not self.evaluator_prompt_path.exists():
            raise FileNotFoundError(f"Evaluator prompt not found at {self.evaluator_prompt_path}")
            
        eval_prompt_template = self.evaluator_prompt_path.read_text(encoding="utf-8")
        
        # Convert resume json to string for prompt
        resume_str = json.dumps(resume_json, indent=2)
        
        final_prompt = f"""{eval_prompt_template}

JOB DESCRIPTION:
{clean_jd}

GENERATED RESUME JSON:
{resume_str}
"""
        print(f"      ⚖️  Evaluating resume with Gemini...")
        evaluation = self.llm.generate_json("gemini", final_prompt, temperature=0.2)
        return evaluation

    def process_complete_workflow(self, job: Job) -> bool:
        """
        Run the full generation pipeline for a single job.
        Returns True if successful (package generated), False otherwise.
        """
        print(f"\n🎯 PROCESSING JOB: {job.title}")
        
        # 1. Hybrid Cleaning & Filtering
        print("   🧹 Hybrid Cleaning: Regex Trim...")
        # Step A: Regex Trim
        raw_trimmed = trim_jd_smart(job.description)
        
        # Step B: Fast Sponsorship Fail
        is_safe, reason = check_sponsorship_viability(raw_trimmed)
        if not is_safe:
             print(f"      ⛔ BLOCKER (Regex): {reason}")
             return False

        # Step C: AI Cleaning (Refining the trimmed text)
        print("   🤖 AI Refining JD...")
        clean_jd = self.clean_jd(raw_trimmed)
        
        # 2. Check Relevance (AI Layer 2)
        print("   🔍 Checking Relevance...")
        relevance = self.check_relevance(clean_jd)
        if not relevance.get('relevant', False):
            print(f"   ⏭️  Skipping: {relevance.get('reason', 'Not relevant')}")
            if relevance.get('blocking_issue'):
                 print(f"      ⛔ BLOCKER: {relevance.get('blocking_issue')}")
            return False
            
        print("   ✅ Job is Relevant.")
        
        # 3. Resume Generation Loop (Iterative Refinement)
        max_retries = 3
        current_attempt = 0
        resume_json = self.generate_resume(job, clean_jd)
        
        if not resume_json:
            print("   ❌ Failed to generate resume JSON.")
            return False

        while current_attempt <= max_retries:
            # 4. Evaluate
            try:
                eval_result = self.evaluate_resume(job, clean_jd, resume_json)
                score_val = eval_result.get('total_score') or eval_result.get('overall_score')
                
                # Handle "85/100" or int
                try:
                    if isinstance(score_val, str) and "/" in score_val:
                        score = int(score_val.split("/")[0])
                    else:
                        score = int(score_val) if score_val is not None else 0
                except:
                    score = 0
                    
                print(f"   📊 Evaluation Score: {score}/100")
                
                # Check Threshold
                if score >= 85:
                    print(f"   ✅ Score met threshold (85). Proceeding.")
                    break
                
                if current_attempt >= max_retries:
                    print(f"   ⚠️ Max retries reached. Using current resume.")
                    break
                    
                # Optimize
                print(f"   🔧 Score < 85. Refining resume (Attempt {current_attempt + 1}/{max_retries})...")
                feedback = json.dumps(eval_result, indent=2)
                optimized_json = self.optimize_resume(job, clean_jd, resume_json, feedback)
                
                # Merge with previous resume to handle "[unchanged]" placeholders
                resume_json = self._merge_resumes(resume_json, optimized_json)
                
                current_attempt += 1
                
            except Exception as e:
                print(f"   ⚠️ Evaluation/Optimization error: {e}")
                break
            
        # 5. Compile PDF
        # Ensure we have a job directory
        import re
        safe_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', job.title).strip()
        safe_company = re.sub(r'[^a-zA-Z0-9_\- ]', '', job.company).strip() or "Unknown"
        folder_name = f"{safe_company} - {safe_title}"[:60]
        
        job_dir = self.output_dir / folder_name
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Save artifacts
        (job_dir / "clean_jd.txt").write_text(clean_jd, encoding="utf-8")
        (job_dir / "resume.json").write_text(json.dumps(resume_json, indent=2), encoding="utf-8")
        (job_dir / "apply_url.txt").write_text(job.apply_url or "", encoding="utf-8")
        
        # Compile
        from job_automation.core.pdf_compiler import PDFCompiler
        compiler = PDFCompiler(template_dir=self.root_dir)
        
        success = compiler.compile(resume_json, job_dir / "resume.pdf", "resume_template.tex")
        if success:
            print(f"   ✅ PDF Generated: {job_dir / 'resume.pdf'}")
        else:
            print(f"   ❌ PDF Compilation failed.")

        # 6. Save meta.json (CRITICAL for Chrome Extension Sync)
        # This makes the job instantly visible in the SmartJobApply Extension
        from datetime import datetime
        meta_content = {
            "company": job.company,
            "title": job.title,
            "job_url": job.url,
            "apply_url": job.apply_url,
            # Use summary or first 500 chars of resume as preview
            "resume_text": resume_json.get("summary", "")[:500],
            "status": "generated",
            "created_at": str(datetime.now())
        }
        (job_dir / "meta.json").write_text(json.dumps(meta_content, indent=2), encoding="utf-8")
        print(f"      ✓ Synced to Chrome Extension (meta.json created)")
        
        return success
            
        return success

    def optimize_resume(self, job: Job, clean_jd: str, current_resume: Dict, feedback: str) -> Dict[str, Any]:
        """Iteratively improve resume using Legacy Feedback Loop."""
        final_prompt = self._build_writer_prompt(job, clean_jd, current_resume, feedback)
        return self.llm.generate_json("deepseek", final_prompt, temperature=0.7)

    def _merge_resumes(self, old: Any, new: Any) -> Any:
        """
        Recursively merge new resume into old resume.
        If new value contains "unchanged", keep old value.
        """
        if isinstance(new, dict) and isinstance(old, dict):
            merged = old.copy()
            for k, v in new.items():
                if k in merged:
                    merged[k] = self._merge_resumes(merged[k], v)
                else:
                    merged[k] = v
            return merged
        elif isinstance(new, list):
            # For lists, if ANY item is "[unchanged]", we might need complex logic.
            # But usually usually "unchanged" is a string.
            # If the list itself is "[unchanged]", it's a string, not a list.
            # If the list contains strings like "[unchanged]", we keep old items?
            # Iteration prompt usually returns FULL lists.
            # Let's assume replacement for simplicity unless explicit marker found.
            return new
        elif isinstance(new, str):
            if "unchanged" in new.lower() and len(new) < 50:
                return old
            return new
        else:
            return new
