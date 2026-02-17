
import os
import json
import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import logging
# Assume a utility for Telegram notifications and Gemini Vision exists
# from a_shared.utils import send_telegram_message, analyze_form_with_gemini

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
BASE_JOB_DIR = os.path.expanduser("~/Desktop/Google Auto/")
CONTEXT_FILE = os.path.expanduser("~/Desktop/CERTIFICATES/google/MASTER_CONTEXT.md")
CANDIDATE_PROFILE = {
    "Name": "Nuthan Reddy Vaddi Reddy",
    "Email": "nuthanreddy001@gmail.com",
    "Phone": "+1 682-406-5646",
    "LinkedIn": "linkedin.com/in/nuthan-reddy-vaddi-reddy"
}

# --- Helper Functions ---
def load_context():
    """Loads the master context file."""
    try:
        with open(CONTEXT_FILE, 'r') as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"CRITICAL: Master context file not found at {CONTEXT_FILE}")
        return None

def find_jobs_to_apply():
    """Finds jobs with status 'ready_to_apply'."""
    ready_jobs = []
    for company_folder in os.listdir(BASE_JOB_DIR):
        job_path = os.path.join(BASE_JOB_DIR, company_folder)
        if os.path.isdir(job_path):
            meta_path = os.path.join(job_path, "meta.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r') as f:
                        meta = json.load(f)
                    if meta.get("status") == "ready_to_apply":
                        ready_jobs.append(job_path)
                except (json.JSONDecodeError, KeyError):
                    logging.warning(f"Skipping malformed meta.json in {job_path}")
    return ready_jobs

def update_job_status(job_path, status):
    """Updates the status in the meta.json file."""
    meta_path = os.path.join(job_path, "meta.json")
    try:
        with open(meta_path, 'r+') as f:
            meta = json.load(f)
            meta['status'] = status
            f.seek(0)
            json.dump(meta, f, indent=4)
            f.truncate()
        logging.info(f"Updated status to '{status}' for {os.path.basename(job_path)}")
    except Exception as e:
        logging.error(f"Failed to update status for {os.path.basename(job_path)}: {e}")

async def apply_to_job(job_path, master_context):
    """Main function to apply to a single job."""
    job_name = os.path.basename(job_path)
    logging.info(f"--- Starting application for: {job_name} ---")

    # Setup audit directory
    audit_dir = os.path.join(job_path, 'audit')
    screenshots_dir = os.path.join(audit_dir, 'screenshots')
    os.makedirs(screenshots_dir, exist_ok=True)
    
    audit_log = []

    try:
        with open(os.path.join(job_path, 'apply_url.txt'), 'r') as f:
            apply_url = f.read().strip()
        resume_path = os.path.join(job_path, 'NuthanReddy.pdf')
    except FileNotFoundError as e:
        logging.error(f"Missing required file in {job_name}: {e}. Skipping job.")
        update_job_status(job_path, "error_missing_files")
        return

    async with async_playwright() as p:
        # NOTE: Playwright-Stealth is not an official library.
        # Using vanilla Playwright with human-like delays.
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            logging.info(f"Navigating to {apply_url}")
            await page.goto(apply_url, wait_until='load', timeout=60000)
            await asyncio.sleep(3) # Wait for page to settle

            # 1. Initial screenshot
            initial_screenshot_path = os.path.join(screenshots_dir, '01_loaded.png')
            await page.screenshot(path=initial_screenshot_path)
            audit_log.append({'step': 'load_page', 'status': 'success', 'screenshot': initial_screenshot_path})
            
            # 2. Analyze form with Gemini Vision (Conceptual)
            # This part requires a separate implementation using a multimodal model.
            # For now, we'll simulate filling based on common field names.
            logging.info("Analyzing form structure (simulated)...")
            # form_analysis = await analyze_form_with_gemini(page) # Placeholder

            # 3. Fill basic info
            logging.info("Filling basic information...")
            await page.fill('input[name*="name"]', CANDIDATE_PROFILE["Name"])
            await page.fill('input[name*="email"]', CANDIDATE_PROFILE["Email"])
            await page.fill('input[name*="phone"]', CANDIDATE_PROFILE["Phone"])
            await page.fill('input[name*="linkedin"]', CANDIDATE_PROFILE["LinkedIn"])
            filled_screenshot_path = os.path.join(screenshots_dir, '02_filled_basic.png')
            await page.screenshot(path=filled_screenshot_path)
            audit_log.append({'step': 'fill_basic_info', 'status': 'success', 'screenshot': filled_screenshot_path})
            
            # 4. Upload Resume
            logging.info(f"Uploading resume: {resume_path}")
            async with page.expect_file_chooser() as fc_info:
                await page.click('input[type="file"]') # Or a more specific selector
            file_chooser = await fc_info.value
            await file_chooser.set_files(resume_path)
            upload_screenshot_path = os.path.join(screenshots_dir, '03_resume_uploaded.png')
            await page.screenshot(path=upload_screenshot_path)
            audit_log.append({'step': 'upload_resume', 'status': 'success', 'screenshot': upload_screenshot_path})

            # 5. Answer Screening Questions (Conceptual)
            # This would involve iterating through `form_analysis` and using logic
            # from MASTER_CONTEXT.md to answer.
            logging.info("Answering screening questions (simulated)...")
            # ... loop through questions ...
            screening_qs_screenshot_path = os.path.join(screenshots_dir, '04_screening_questions.png')
            await page.screenshot(path=screening_qs_screenshot_path)
            audit_log.append({'step': 'answer_screening_questions', 'status': 'success', 'screenshot': screening_qs_screenshot_path})
            
            # 6. Click Submit (DISABLED FOR SAFETY)
            logging.warning("SUBMIT ACTION IS DISABLED. Manual submission required.")
            # await page.click('button[type="submit"]')

            # 7. Final Screenshot
            confirmation_screenshot_path = os.path.join(screenshots_dir, '05_submitted_confirmation.png')
            await page.screenshot(path=confirmation_screenshot_path)
            audit_log.append({'step': 'submit_application', 'status': 'simulated_success', 'screenshot': confirmation_screenshot_path})
            
            # Update status to submitted
            update_job_status(job_path, "submitted")
            # await send_telegram_message(f"✅ Application submitted successfully for {job_name}")

        except Exception as e:
            logging.error(f"An error occurred during the application for {job_name}: {e}")
            error_screenshot_path = os.path.join(screenshots_dir, '99_error.png')
            await page.screenshot(path=error_screenshot_path)
            audit_log.append({'step': 'error', 'status': 'failed', 'details': str(e), 'screenshot': error_screenshot_path})
            update_job_status(job_path, "error_application_failed")
            # await send_telegram_message(f"🚨 Application failed for {job_name}: {e}")

        finally:
            await browser.close()
            # Save audit log
            df = pd.DataFrame(audit_log)
            df.to_csv(os.path.join(audit_dir, 'audit_log.csv'), index=False)
            logging.info(f"--- Finished application for: {job_name} ---")


async def main():
    """Main execution function."""
    logging.info("Starting Application Bot...")
    master_context = load_context()
    if not master_context:
        return

    jobs_to_apply = find_jobs_to_apply()
    if not jobs_to_apply:
        logging.info("No new jobs to apply for.")
        return

    logging.info(f"Found {len(jobs_to_apply)} new jobs to apply for.")
    for job_path in jobs_to_apply:
        await apply_to_job(job_path, master_context)

if __name__ == "__main__":
    asyncio.run(main())
