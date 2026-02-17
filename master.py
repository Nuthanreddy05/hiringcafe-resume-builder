
import subprocess
import logging
import sys
import os
import time

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
BASE_SCRIPT_DIR = os.path.expanduser("~/Desktop/CERTIFICATES/google/")
APPLICATION_BOT_SCRIPT = os.path.join(BASE_SCRIPT_DIR, "application_bot.py")
QA_AUDITOR_SCRIPT = os.path.join(BASE_SCRIPT_DIR, "qa_auditor.py")

def run_script(script_path):
    """Runs a Python script as a separate process and waits for it to complete."""
    if not os.path.exists(script_path):
        logging.error(f"Script not found: {script_path}")
        return False
    
    try:
        logging.info(f"--- Running script: {os.path.basename(script_path)} ---")
        process = subprocess.Popen([sys.executable, script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Stream output in real-time
        for line in process.stdout:
            logging.info(f"[{os.path.basename(script_path)}] {line.strip()}")
        for line in process.stderr:
            logging.error(f"[{os.path.basename(script_path)}] {line.strip()}")
            
        process.wait() # Wait for the process to finish
        
        if process.returncode == 0:
            logging.info(f"--- Script finished successfully: {os.path.basename(script_path)} ---")
            return True
        else:
            logging.error(f"--- Script failed with return code {process.returncode}: {os.path.basename(script_path)} ---")
            return False
            
    except Exception as e:
        logging.error(f"An exception occurred while running {script_path}: {e}")
        return False

def main():
    """Main orchestrator function."""
    logging.info("=============================================")
    logging.info("  Starting Master Job Application Orchestrator  ")
    logging.info("=============================================")

    # Step 1: Run the Application Bot to process new jobs
    logging.info("\n>>> STEP 1: Searching for new jobs and applying...")
    success = run_script(APPLICATION_BOT_SCRIPT)
    if not success:
        logging.error("Application bot failed. Halting orchestration.")
        # Optionally send a Telegram failure notification
        return

    logging.info("Application bot finished. Waiting a moment before starting QA...")
    time.sleep(5) # Give a brief pause for file system to sync if needed

    # Step 2: Run the QA Auditor on the newly submitted applications
    logging.info("\n>>> STEP 2: Running QA audit on submitted applications...")
    success = run_script(QA_AUDITOR_SCRIPT)
    if not success:
        logging.error("QA auditor script failed.")
        # Optionally send a Telegram failure notification
        return

    logging.info("\n=============================================")
    logging.info("    Orchestration process completed.    ")
    logging.info("=============================================")
    # Optionally send a Telegram summary notification

if __name__ == "__main__":
    main()
