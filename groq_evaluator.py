def evaluate_resume_with_groq(
    groq_api_key: str,
    latex_content: str,
    job: Job,
    cleaned_jd: str,
    trace_path: Optional[Path] = None,
    audit_logger: Optional['AuditLogger'] = None,
) -> Tuple[int, str, bool]:
    """
    Evaluates resume using Groq (Llama-3.3-70b) when Gemini is unavailable.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }

    # Construct Prompt (Same logic as Gemini)
    prompt = f"""
    You are an Expert ATS Resume Scorer.
    
    JOB DESCRIPTION:
    {cleaned_jd[:4000]}
    
    CANDIDATE RESUME (LaTeX):
    {latex_content[:4000]}
    
    TASK:
    Rate this resume on a scale of 0-100 based on how well it matches the JD.
    Provide constructive feedback.
    
    OUTPUT FORMAT:
    RATING: [Score]
    FEEDBACK: [1-2 sentences of specific advice]
    STATUS: [READY or NOT READY]
    """
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    try:
        if trace_path: log_trace(trace_path, "Groq EVAL REQUEST", prompt)
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        result_text = response.json()['choices'][0]['message']['content']
        
        if trace_path: log_trace(trace_path, "Groq EVAL RESPONSE", result_text)
        if audit_logger: audit_logger.log("08_evaluator_feedback_groq.txt", result_text)
        
        # Parse Score
        score = 0
        match = re.search(r"RATING:[\s*]*(\d+)", result_text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            
        # Parse Status
        approved = "READY" in result_text.upper() or score >= 80
        
        return score, result_text, approved
        
    except Exception as e:
        print(f"      ⚠️ Groq Evaluation Failed: {e}")
        return 0, f"Evaluation Error: {e}", False
