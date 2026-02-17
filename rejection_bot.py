
import os
import json
import logging
import base64
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import requests

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
BASE_JOB_DIR = os.path.expanduser("~/Desktop/Google Auto/")
CONTEXT_FILE = os.path.expanduser("~/Desktop/CERTIFICATES/google/MASTER_CONTEXT.md")
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_PATH = os.path.expanduser('~/Desktop/CERTIFICATES/google/credentials.json') # IMPORTANT: Get this from Google Cloud Console
TOKEN_PATH = os.path.expanduser('~/Desktop/CERTIFICATES/google/token.json')
NVIDIA_API_KEY = "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"
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1"
DEEPSEEK_MODEL = "deepseek-ai/deepseek-v3.1-terminus"

# --- Gmail Authentication ---
def get_gmail_service():
    """Authenticates with Gmail API and returns the service object."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                logging.error(f"CRITICAL: Gmail credentials.json not found at {CREDENTIALS_PATH}")
                logging.error("Please enable the Gmail API in Google Cloud Console and download the credentials.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

# --- DeepSeek Analysis ---
def call_deepseek_api(prompt):
    """Calls the NVIDIA DeepSeek API for analysis."""
    headers = { "Authorization": f"Bearer {NVIDIA_API_KEY}", "Accept": "application/json" }
    payload = {
        "model": DEEPSEEK_MODEL, "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2, "top_p": 0.7, "max_tokens": 1024,
    }
    try:
        response = requests.post(f"{NVIDIA_API_URL}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        logging.error(f"API call failed: {e}")
        return '{"error": "API call failed"}'

# --- Email Processing ---
def scan_emails(service):
    """Scans emails from the last 7 days for rejection patterns."""
    rejection_emails = []
    query_date = (datetime.now() - timedelta(days=7)).strftime('%Y/%m/%d')
    query = f'after:{query_date} ("thank you for your application" OR "update on your application" OR "decided to move forward with other candidates")'
    
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])

    if not messages:
        logging.info("No potential rejection emails found in the last 7 days.")
        return []

    logging.info(f"Found {len(messages)} potential rejection emails. Analyzing content...")
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = msg_data['payload']['headers']
        subject = next(h['value'] for h in headers if h['name'] == 'Subject')
        
        if 'parts' in msg_data['payload']:
            body_data = msg_data['payload']['parts'][0]['body']['data']
        else:
            body_data = msg_data['payload']['body']['data']
        
        body = base64.urlsafe_b64decode(body_data).decode('utf-8')

        # Basic filtering to reduce noise before sending to AI
        rejection_keywords = ["not moving forward", "other candidates", "position has been filled", "pursue other applicants"]
        if any(keyword in body.lower() for keyword in rejection_keywords):
            rejection_emails.append({'subject': subject, 'body': body})
    
    return rejection_emails

def analyze_rejections(emails, master_context):
    """Analyzes a batch of rejection emails to find patterns."""
    if not emails:
        return "No rejections to analyze."

    emails_formatted = "\n---\n".join([f"Subject: {e['subject']}\nBody: {e['body'][:500]}..." for e in emails])

    prompt = f"""
    You are a career strategy analyst. You have been given a batch of job application rejection emails from the past week.
    Your task is to analyze them and generate a concise report on patterns and suggest improvements.

    **MASTER CONTEXT (for understanding rejection patterns):**
    {master_context}

    **REJECTION EMAILS FROM THE LAST 7 DAYS:**
    ---
    {emails_formatted}
    ---

    **ANALYSIS TASK:**
    Based on the emails and the master context, generate a report with the following structure:
    1.  **Total Rejections:** Count the number of emails that are definitively rejections.
    2.  **Company/ATS Patterns:** Can you identify which companies sent these rejections? Do you see patterns related to specific Applicant Tracking Systems (e.g., automated Workday emails)?
    3.  **Common Themes:** Are there common phrases or reasons cited in the rejections?
    4.  **Actionable Recommendations:** Based on these rejections, suggest ONE key adjustment to the job application strategy. For example, "Focus more on startups as they seem to have a manual review process," or "Improve keyword matching for resumes submitted to Workday."

    **OUTPUT FORMAT (Strictly JSON):**
    {{
      "total_rejections": <integer>,
      "rejection_rate_benchmark": "<From the master context, e.g., 'Normal (15-30%)'>",
      "company_patterns": [
        {{
          "company_name": "<Extracted Company Name>",
          "possible_ats": "<Workday, Greenhouse, Lever, or Unknown>"
        }}
      ],
      "common_themes": ["<Theme 1>", "<Theme 2>"],
      "strategic_recommendations": "<A single, concise recommendation for strategy improvement.>"
    }}
    """
    
    logging.info("Sending rejection batch to DeepSeek for analysis...")
    return call_deepseek_api(prompt)

def main():
    """Main execution function."""
    logging.info("Starting Rejection Analyzer Bot...")
    service = get_gmail_service()
    if not service:
        return

    master_context = ""
    try:
        with open(CONTEXT_FILE, 'r') as f:
            master_context = f.read()
    except FileNotFoundError:
        logging.error(f"Master context file not found at {CONTEXT_FILE}")
        return

    rejection_emails = scan_emails(service)
    
    if rejection_emails:
        analysis_report = analyze_rejections(rejection_emails, master_context)
        report_path = os.path.expanduser(f"~/Desktop/CERTIFICATES/google/rejection_report_{datetime.now().strftime('%Y-%m-%d')}.json")
        try:
            report_json = json.loads(analysis_report)
            with open(report_path, 'w') as f:
                json.dump(report_json, f, indent=4)
            logging.info(f"Weekly rejection analysis complete. Report saved to {report_path}")
            # send_telegram_message("✅ Weekly rejection analysis complete. See report for details.")
        except json.JSONDecodeError:
            logging.error("Failed to decode the analysis report into JSON.")
            # send_telegram_message("🚨 Failed to generate weekly rejection report. API response was not valid JSON.")
    else:
        logging.info("No new rejections to analyze this week.")


if __name__ == "__main__":
    main()
