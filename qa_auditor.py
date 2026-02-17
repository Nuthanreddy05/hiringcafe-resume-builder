
import os
import json
import pandas as pd
import logging
import requests
from pathlib import Path

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
BASE_JOB_DIR = os.path.expanduser("~/Desktop/Google Auto/")
CONTEXT_FILE = os.path.expanduser("~/Desktop/CERTIFICATES/google/MASTER_CONTEXT.md")
NVIDIA_API_KEY = "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" # Replace with env variable
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1"
DEEPSEEK_MODEL = "deepseek-ai/deepseek-v3.1-terminus"

# --- Helper Functions ---
def load_file_content(path, file_type="text"):
    """Loads content from a file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logging.warning(f"File not found: {path}")
        return None
    except Exception as e:
        logging.error(f"Error reading {path}: {e}")
        return None

def call_deepseek_api(prompt):
    """Calls the NVIDIA DeepSeek API for analysis."""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "top_p": 0.7,
        "max_tokens": 1024,
    }
    try:
        response = requests.post(f"{NVIDIA_API_URL}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        logging.error(f"API call failed: {e}")
        return f'{{"error": "API call failed: {e}"}}'

def run_qa_for_job(job_path):
    """Performs QA for a single submitted job."""
    job_name = os.path.basename(job_path)
    logging.info(f"--- Starting QA for: {job_name} ---")

    # Load necessary files
    master_context = load_file_content(CONTEXT_FILE)
    jd_text = load_file_content(os.path.join(job_path, 'JD.txt'))
    resume_text = load_file_content(os.path.join(job_path, 'resume.txt'))
    audit_log_path = os.path.join(job_path, 'audit', 'audit_log.csv')
    
    if not all([master_context, jd_text, resume_text, os.path.exists(audit_log_path)]):
        logging.error(f"Missing one or more required files for QA in {job_name}. Skipping.")
        return

    audit_log_df = pd.read_csv(audit_log_path)
    audit_log_summary = audit_log_df.to_string()

    # Create the prompt for DeepSeek
    prompt = f"""
    You are a meticulous QA Auditor for a job application bot. Your task is to analyze a submitted application and provide a quality score and a detailed report.

    **MASTER CONTEXT (Abbreviated Rules):**
    {master_context}

    **JOB DESCRIPTION:**
    ---
    {jd_text}
    ---

    **CANDIDATE'S RESUME (for this specific job):**
    ---
    {resume_text}
    ---

    **APPLICATION AUDIT LOG (what the bot did):**
    ---
    {audit_log_summary}
    ---

    **YOUR TASK:**
    Based on all the provided information, please perform the following analysis:
    1.  **Discrepancy Check:** Compare the actions in the audit log against the resume and the job description. Were the answers to screening questions (even if simulated) consistent with the candidate's experience in the resume?
    2.  **Alignment Check:** Does the submitted application align well with the job description and the rules in the master context? (e.g., did it apply for a job requiring clearance?).
    3.  **Red Flag Identification:** Identify any potential issues, errors, or red flags that could lead to an automatic rejection.
    4.  **Scoring:** Provide a quality score from 0 to 100, where 100 is a perfect, highly-aligned application.
    5.  **Recommendation:** Based on the score, recommend 'APPROVE' (score >= 80) or 'REVIEW_MANUALLY' (score < 80).

    **OUTPUT FORMAT (Strictly JSON):**
    Please provide your response in a single JSON object.
    {{
      "quality_score": <integer>,
      "recommendation": "<APPROVE or REVIEW_MANUALLY>",
      "issues": [
        {{
          "severity": "<HIGH|MEDIUM|LOW>",
          "description": "<Detailed description of the issue found>"
        }}
      ],
      "reasoning": "<Your detailed step-by-step reasoning for the score and findings. Explain what you checked and why.>"
    }}
    """

    logging.info(f"Sending request to DeepSeek for {job_name}...")
    api_response = call_deepseek_api(prompt)

    try:
        qa_report = json.loads(api_response)
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON response from API for {job_name}.")
        qa_report = {
            "quality_score": 0,
            "recommendation": "REVIEW_MANUALLY",
            "issues": [{"severity": "HIGH", "description": "Failed to parse API response."}],
            "reasoning": f"The API returned a non-JSON response:\n{api_response}"
        }

    # Save the report
    report_path = os.path.join(job_path, 'audit', 'qa_report.json')
    with open(report_path, 'w') as f:
        json.dump(qa_report, f, indent=4)

    logging.info(f"QA report generated for {job_name}. Score: {qa_report.get('quality_score')}")
    
    if qa_report.get('quality_score', 0) < 80:
        logging.warning(f"Job {job_name} flagged for manual review.")
        # send_telegram_message(f"⚠️ QA score < 80 for {job_name}. Needs manual review.")


def find_jobs_to_audit():
    """Finds jobs with status 'submitted' that need a QA report."""
    audit_jobs = []
    for company_folder in os.listdir(BASE_JOB_DIR):
        job_path = os.path.join(BASE_JOB_DIR, company_folder)
        if os.path.isdir(job_path):
            meta_path = os.path.join(job_path, "meta.json")
            qa_report_path = os.path.join(job_path, 'audit', 'qa_report.json')
            if os.path.exists(meta_path) and not os.path.exists(qa_report_path):
                try:
                    with open(meta_path, 'r') as f:
                        meta = json.load(f)
                    if meta.get("status") == "submitted":
                        audit_jobs.append(job_path)
                except (json.JSONDecodeError, KeyError):
                    continue
    return audit_jobs

def main():
    """Main execution function."""
    logging.info("Starting QA Auditor...")
    jobs_to_audit = find_jobs_to_audit()

    if not jobs_to_audit:
        logging.info("No new submissions to audit.")
        return

    logging.info(f"Found {len(jobs_to_audit)} submissions to audit.")
    for job_path in jobs_to_audit:
        run_qa_for_job(job_path)

if __name__ == "__main__":
    main()
