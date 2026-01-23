
def generate_resume_json_deepseek(
    deepseek_client: OpenAI,
    base_resume_json: str, # Passed as string of JSON
    resume_prompt: str,
    job: Job,
    cleaned_jd: str,
    trace_path: Optional[Path] = None,
    audit_logger: Optional['AuditLogger'] = None,
) -> dict:
    """Use DeepSeek to generate tailored resume CONTENT (JSON only)"""
    
    # [v2.0 Logic] Calculate Soft Skills Ratio
    soft_skills = ["communication", "collaboration", "teamwork", "leadership", "mentoring", "ownership", "problem-solving"]
    soft_count = sum(1 for s in soft_skills if s in cleaned_jd.lower())
    total_words = len(cleaned_jd.split())
    # Heuristic: Approximate keyword density
    soft_ratio = str(round(soft_count / (total_words * 0.05 + 1), 2)) # Normalized ratio
    
    prompt = f"""{resume_prompt}

JOB INFORMATION:
Title: {job.title}
Company: {job.company}
Soft Skills Ratio: {soft_ratio} (>0.1 suggests higher weight)

JOB DESCRIPTION (trimmed):
{cleaned_jd}

BASE RESUME JSON:
{base_resume_json}
"""

    if trace_path:
        log_trace(trace_path, "DeepSeek JSON GENERATION Prompt", prompt)
    
    if audit_logger:
        audit_logger.log("05_writer_prompt.txt", prompt)

    try:
        response = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "You are a JSON generator. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={ "type": "json_object" } # DeepSeek supports this
        )
        
        content = response.choices[0].message.content.strip()
        
        # Cleanup markdown if present
        if "```" in content:
             content = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", content, flags=re.DOTALL | re.IGNORECASE)

        json_data = json.loads(content)
        
        if trace_path:
            log_trace(trace_path, "DeepSeek JSON GENERATION Output", json.dumps(json_data, indent=2))
        
        if audit_logger:
            audit_logger.log("06_generated_content.json", json.dumps(json_data, indent=2))
             
        return json_data
    
    except Exception as e:
        print(f"      ❌ DeepSeek Generation Failed: {e}")
        # Fallback: return empty dict or try to parse partial
        return {}


def evaluate_resume_with_gemini(
    gemini_client: genai.Client,
    resume_latex: str,
    job: Job,
    cleaned_jd: str,
    prompt_template: str,
    trace_path: Optional[Path] = None,
    audit_logger: Optional['AuditLogger'] = None,
) -> Tuple[int, str, bool]:
    """Use Gemini to evaluate resume quality and provide feedback"""
    
    # Inject dynamic values into template
    current_date = datetime.now().strftime("%B %Y")
    prompt = prompt_template.replace("{current_date}", current_date)
    
    # Construct the full prompt context
    full_prompt = f"""
{prompt}

*** RESUME TO EVALUATE (LaTeX Source) ***
{resume_latex}

*** JOB DESCRIPTION ***
{cleaned_jd}
"""

    try:
        if audit_logger:
            audit_logger.log("07_evaluation_prompt.md", full_prompt)
            
        print(f"      -> Sending to Gemini ({GEMINI_MODEL})...")
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.2, # Low temperature for strict evaluation
            )
        )
        
        evaluation_text = response.text
        
        if audit_logger:
            audit_logger.log("08_evaluation_raw_response.md", evaluation_text)

        # Parse Score using regex
        score_match = re.search(r"TOTAL SCORE:\s*(\d+)/100", evaluation_text)
        score = int(score_match.group(1)) if score_match else 0
        
        # Parse Status
        approved = False
        if "STATUS: APPROVED" in evaluation_text or "STATUS: GRADUATED" in evaluation_text or "STATUS: READY FOR SUBMISSION" in evaluation_text:
            approved = True
        elif score >= APPROVAL_THRESHOLD:
            approved = True
            
        return score, evaluation_text, approved
        
    except Exception as e:
        print(f"      ❌ Gemini Evaluation Failed: {e}")
        return 0, f"Evaluation failed: {e}", False


# ============================================================================
# LaTeX Compilation
# ============================================================================

def sanitize_latex(tex: str) -> str:
    """Clean LaTeX to reduce compile errors"""
    if not tex:
        return tex
    
    # Keep only from \documentclass
    i = tex.find("\\documentclass")
    if i != -1:
        tex = tex[i:]
    
    # Escape unescaped ampersands (outside tabular)
    lines = tex.splitlines()
    out_lines = []
    in_tabular = False
    
    for line in lines:
        if re.search(r"\\begin\{(tabular|array|align)", line):
            in_tabular = True
        if re.search(r"\\end\{(tabular|array|align)", line):
            in_tabular = False
        
        if not in_tabular:
            line = re.sub(r"(?<!\\)&", r"\\&", line)
        
        out_lines.append(line)
    
    return "\n".join(out_lines)


def compile_latex_to_pdf(latex_content: str, output_dir: Path, output_name: str = "NuthanReddy") -> Optional[Path]:
    """Compile LaTeX to PDF using tectonic"""
    
    latex_content = sanitize_latex(latex_content)
    
    build_dir = output_dir / "_build"
    build_dir.mkdir(parents=True, exist_ok=True)
    
    tex_file = build_dir / f"{output_name}.tex"
    tex_file.write_text(latex_content, encoding="utf-8")
    
    print(f"\n   🔨 Compiling LaTeX to PDF...")
    
    cmd = [
        "tectonic",
        "-X", "compile",
        "--untrusted",
        str(tex_file),
        "--outdir", str(build_dir),
        "--keep-logs",
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"      ✗ Compilation failed:")
            print(f"      STDERR: {result.stderr[:500]}")
            return None
        
        pdf_file = build_dir / f"{output_name}.pdf"
        if not pdf_file.exists():
            print(f"      ✗ PDF not found at {pdf_file}")
            return None
        
        print(f"      ✓ PDF compiled successfully")
        return pdf_file
    
    except subprocess.TimeoutExpired:
        print(f"      ✗ Compilation timeout")
        return None
    except Exception as e:
        print(f"      ✗ Compilation error: {e}")
        return None


# ============================================================================
# Package Saving
# ============================================================================

def save_job_package(
    output_root: Path,
    job: Job,
    cleaned_jd: str,
    best_iteration: IterationResult,
    all_iterations: List[IterationResult],
    pdf_path: Path,
) -> Path:
    """Save complete job application package"""
    
    folder_name = build_folder_name(job)
    package_dir = output_root / folder_name
    package_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n   💾 Saving package to: {folder_name}/")
    
    # 1. Save JD
    (package_dir / "JD.txt").write_text(cleaned_jd, encoding="utf-8")
    
    # 2. Save apply URL
    (package_dir / "apply_url.txt").write_text(job.apply_url + "\n", encoding="utf-8")
    
    # 3. Save best resume LaTeX
    (package_dir / "resume.tex").write_text(best_iteration.latex_content, encoding="utf-8")
    
    # 4. Copy PDF as NuthanReddy.pdf
    final_pdf = package_dir / "NuthanReddy.pdf"
    final_pdf.write_bytes(pdf_path.read_bytes())
    
    # 5. Save metadata
    metadata = {
        "job_url": job.url,
        "apply_url": job.apply_url,
        "title": job.title,
        "company": job.company,
        "job_id": build_job_id(job),
        "scraped_at": datetime.now().isoformat(),
        "best_iteration": best_iteration.iteration,
        "best_score": best_iteration.gemini_score,
        "total_iterations": len(all_iterations),
        "models_used": {
            "writer": DEEPSEEK_MODEL,
            "evaluator": GEMINI_MODEL,
        }
    }
    (package_dir / "meta.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    
    # 6. Save all iterations log
    iterations_log = []
    for it in all_iterations:
        iterations_log.append({
            "iteration": it.iteration,
            "score": it.gemini_score,
            "feedback": it.gemini_feedback,
            "latex_length": len(it.latex_content),
        })
    (package_dir / "iterations.json").write_text(json.dumps(iterations_log, indent=2), encoding="utf-8")
    
    print(f"      ✓ Saved: JD.txt, apply_url.txt, resume.tex, NuthanReddy.pdf, meta.json, iterations.json")
    
    return package_dir


# ============================================================================
# Main Orchestration
# ============================================================================

def main_hiringcafe():
    parser = argparse.ArgumentParser(
        description="HiringCafe Job Application Automation with DeepSeek + Gemini"
    )
    import csv
    # job_aggregator is imported at top of file, no need to import here again if it was in lines 1-1400.
    # But just in case:
    try:
        import job_aggregator
    except ImportError:
        pass # Assuming unused if running scrape_full_jd logic inline

    parser.add_argument("--start_url", required=True, help="HiringCafe search URL with filters")
    parser.add_argument("--max_jobs", type=int, default=5, help="Maximum jobs to process")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--out_dir", default=str(Path.home() / "Desktop" / "Google Auto"), help="Output directory")
    parser.add_argument("--profile", default="profile.json", help="Path to profile.json for auto-submission")
    parser.add_argument("--base_resume", default="base_resume.tex", help="Base LaTeX resume template")
    parser.add_argument("--resume_prompt", default="resume_json_prompt.txt", help="Resume customization instructions (JSON mode)")
    parser.add_argument("--evaluator_prompt", default="resume_evaluator_prompt_v3.txt", help="Evaluator instructions")
    parser.add_argument("--resume_template", default="resume_template.tex", help="Jinja2 LaTeX template")
    parser.add_argument("--audit", action="store_true", help="Enable visual audit mode")
    
    args = parser.parse_args()
    
    # Load .env manually
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    try:
                        key, val = line.strip().split("=", 1)
                        os.environ[key] = val.strip("'").strip('"')
                    except: pass

    # Validate API keys
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("❌ ERROR: DEEPSEEK_API_KEY not set")
        return
    
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ ERROR: GEMINI_API_KEY not set")
        return
    
    # Initialize API clients
    deepseek_client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    profile_path = Path(args.profile)
    if not profile_path.exists():
         print(f"❌ ERROR: Profile not found: {profile_path}")
         return
    
    with open(profile_path) as f:
        profile = json.load(f)

    # Load Files
    base_resume_path = Path(args.base_resume)
    resume_prompt_path = Path(args.resume_prompt)
    evaluator_prompt_path = Path(args.evaluator_prompt)
    template_path = str(Path(args.resume_template).resolve())
    
    if not base_resume_path.exists():
        print(f"❌ ERROR: Base resume not found: {base_resume_path}")
        return
        
    if not resume_prompt_path.exists():
        print(f"❌ ERROR: Resume prompt not found: {resume_prompt_path}")
        return

    if not evaluator_prompt_path.exists():
        print(f"❌ ERROR: Evaluator prompt not found: {evaluator_prompt_path}")
        return

    base_resume_tex = base_resume_path.read_text(encoding="utf-8")
    resume_prompt = resume_prompt_path.read_text(encoding="utf-8")
    evaluator_prompt = evaluator_prompt_path.read_text(encoding="utf-8")
    
    output_root = Path(args.out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    
    # Print configuration
    print("=" * 80)
    print("🚀 HIRINGCAFE JOB APPLICATION AUTOMATION")
    print("=" * 80)
    print(f"Start URL:      {args.start_url}")
    print(f"Max jobs:       {args.max_jobs}")
    print(f"Output dir:     {output_root.resolve()}")
    print(f"Writer model:   {DEEPSEEK_MODEL}")
    print(f"Evaluator:      {GEMINI_MODEL}")
    print(f"Approval score: {APPROVAL_THRESHOLD}")
    print(f"Max iterations: {MAX_ITERATIONS}")
    print(f"Headless:       {args.headless}")
    print(f"Evaluator Prompt: {args.evaluator_prompt}")
    print("=" * 80)
    
    # Step 1: Collect job links
    job_links = collect_job_links(args.start_url, args.max_jobs, args.headless)
    
    if not job_links:
        print("\n❌ No job links found. Check your HiringCafe URL.")
        return
    
    # [FIX] Reverse link order (Oldest -> Newest)
    job_links.reverse()
    
    processed = 0
    skipped = 0
    failed = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context()
        
        for idx, job_url in enumerate(job_links, 1):
            print("\n" + "=" * 80)
            print(f"🔍 JOB {idx}/{len(job_links)}")
            print("=" * 80)
            print(f"URL: {job_url}")
            
            try:
                # Fetch job
                job = fetch_job_from_hiringcafe(context, job_url)
                if not job:
                    skipped += 1
                    continue

                # Setup folders
                folder_name = build_folder_name(job)
                job_output_dir = output_root / folder_name
                job_output_dir.mkdir(parents=True, exist_ok=True)
                
                # Check duplication
                if (job_output_dir / "NuthanReddy.pdf").exists():
                    print(f"   ⏩ SKIPPING: Already processed ({folder_name})")
                    processed += 1
                    continue

                trace_path = job_output_dir / "workflow_trace.txt"
                audit_logger = AuditLogger(job.job_id, job.company, output_root, args.audit)
                
                # Log Raw
                audit_logger.log("01_raw_scraped_data.json", json.dumps(job.__dict__, default=str, indent=2))
                audit_logger.log("02_extracted_jd_raw.txt", job.description)
                
                # Clean JD
                trimmed_jd = trim_job_description(job.description)
                trimmed_jd = clean_jd_smart(trimmed_jd)
                print(f"   ✂️  Trimmed JD: {len(trimmed_jd)} chars")

                print(f"   🤖 AI cleaning JD...")
                try:
                    cleaned_jd = ai_clean_jd(trimmed_jd, deepseek_client)
                    print(f"   ✓ Cleaned: {len(trimmed_jd)} -> {len(cleaned_jd)} chars")
                    audit_logger.log("03_jd_cleaning_report.md", f"BEFORE: {len(trimmed_jd)}\nAFTER: {len(cleaned_jd)}\n\n{cleaned_jd}")
                except Exception as e:
                    print(f"   ⚠️  AI cleaning failed: {e}")
                    cleaned_jd = trimmed_jd

                # Relevance check
                audit_logger.log("04_relevance.md", "Skipping explicit relevance check to ensure High Recall.")
                
                # Iteration Loop
                all_iterations = []
                best_iteration = None
                feedback = None 
                current_resume_json = {}

                for i in range(1, MAX_ITERATIONS + 1):
                    print(f"\n   ⚙️  Iteration {i}/{MAX_ITERATIONS}")
                    current_prompt = resume_prompt
                    
                    if feedback:
                        print(f"      Use previous draft + feedback")
                        current_prompt = (
                            resume_prompt + 
                            "\n\n--- PREVIOUS DRAFT JSON ---\n" +
                            json.dumps(best_iteration['resume_data'] if best_iteration else current_resume_json, indent=2) +
                            "\n\n--- FEEDBACK ---\n" + 
                            str(feedback) + 
                            "\n\nINSTRUCTION: Refine based on feedback."
                        )
                    
                    try:
                        # Generate JSON
                        resume_data = generate_resume_json_deepseek(
                            deepseek_client,
                            base_resume_tex, # Use base resume texture as context
                            current_prompt,
                            job,
                            cleaned_jd,
                            trace_path,
                            audit_logger
                        )
                        current_resume_json = resume_data
                        
                        # Render LaTeX
                        generated_latex = render_resume_from_template(template_path, resume_data)
                        print(f"      ✓ Rendered LaTeX")
                        
                        # Evaluate (Gemini)
                        score, feedback, approved = evaluate_resume_with_gemini(
                            gemini_client,
                            generated_latex,
                            job,
                            cleaned_jd,
                            evaluator_prompt, # PASS TEMPLATE HERE
                            trace_path,
                            audit_logger
                        )
                        print(f"      ⭐ Score: {score}/100")

                        iteration_result = IterationResult(
                            iteration=i,
                            resume_json=resume_data,
                            latex_content=generated_latex,
                            gemini_score=score,
                            gemini_feedback=feedback,
                            approved=approved
                        )
                        all_iterations.append(iteration_result)

                        if approved:
                            print(f"      ✅ APPROVED! Score: {score}")
                            best_iteration = iteration_result
                            break
                        else:
                            print(f"      ❌ Not approved. Score: {score}")
                            # Loop will continue
                            
                    except Exception as e:
                        print(f"      ❌ Iteration failed: {e}")
                        feedback = f"Error: {e}"
                        continue
                
                # Post-Loop Handling
                if not best_iteration and all_iterations:
                     best_iteration = max(all_iterations, key=lambda x: x.gemini_score)
                     print(f"   🏆 Using best iteration: score {best_iteration.gemini_score}")

                if best_iteration:
                    pdf_path = compile_latex_to_pdf(best_iteration.latex_content, output_root, "NuthanReddy")
                    if pdf_path:
                        save_job_package(output_root, job, cleaned_jd, best_iteration, all_iterations, pdf_path)
                        print(f"   ✅ Processed: {job.title}")
                        processed += 1
                        print("\n   🚀 Ready for Batch Execution")
                        print(f"      Run: python loader.py --source '{output_root}'")
                    else:
                        print("   ❌ PDF Compile failed")
                        failed += 1
                else:
                    print("   ❌ Failed to generate any valid resume")
                    failed += 1
                    
            except Exception as e:
                print(f"   ❌ Job failed: {e}")
                failed += 1
                continue
                
        context.close()
        browser.close()
    
    # Summary
    print(f"\n✅ Processed: {processed}, ❌ Failed: {failed}")

def main():
    import sys
    # Only using HiringCafe mode for consistency verification
    main_hiringcafe()

if __name__ == "__main__":
    main()
