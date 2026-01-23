#!/usr/bin/env python3
"""
Test script to verify and finetune AI answers without using the browser.
It sends JSON messages to folder_reader.py just like the extension does.
"""

import sys
import json
import subprocess
import os
from pathlib import Path

# Common screening questions to test
TEST_QUESTIONS = [
    "Why do you want to work at Google?",
    "Describe a challenging technical problem you solved.",
    "What is your experience with Python and Machine Learning?",
    "Tell me about a time you had a conflict with a coworker.",
    "What are your salary expectations?"
]

# Mock Context
CONTEXT = {
    "company": "Wavelo",
    "jobTitle": "Data Analyst",
    "jobDescription": "Data Analysis, SQL, Python, Business Intelligence...",
    "url": "https://job-boards.greenhouse.io/wavelo/jobs/7588417003"
}

# Real-ish Resume Text (Simulated)
RESUME_TEXT = """
Nuthan Reddy Vaddireddy
Senior Software Engineer
Summary:
Passionate engineer with 3+ years of experience in Python, specialized in building scalable backend systems and AI integrations. 
At Google (Contract), optimized data pipelines reducing latency by 40%. Implemented RAG architectures using LangChain and Vector Databases.
Proficient in AWS (Lambda, DynamoDB), Docker, and Kubernetes.
Experience:
- Software Engineer at TechCorp: Built a recommendation engine using collaborative filtering.
- Data Analyst Intern: Cleaned messy datasets of 1M+ rows using Pandas.
Education:
- Master's in Computer Science.
"""

# Path to the native host script
HOST_SCRIPT = "./chrome-extension/native-messaging/folder_reader.py"

def run_test():
    print("🚀 Starting AI Answer Calibration...")
    print(f"Target Script: {HOST_SCRIPT}")
    print("-" * 60)

    for i, q in enumerate(TEST_QUESTIONS, 1):
        print(f"\n[Question {i}]: {q}")
        print("🤖 Generating Answer...", end="", flush=True)
        
        message = {
            "action": "generate_answer",
            "question": q,
            "context": CONTEXT,
            "resume_text": RESUME_TEXT,  # Injecting specific resume
            "job_folder_id": "TEST_ID"
        }
        
        # Run the script as a subprocess, feeding stdin
        process = subprocess.Popen(
            [sys.executable, HOST_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Native Messaging Format: Length (4 bytes) + JSON
        msg_json = json.dumps(message).encode('utf-8')
        length_bytes = len(msg_json).to_bytes(4, byteorder='little') # Sys byteorder usually little
        # Python sys.byteorder check
        byte_order = sys.byteorder
        length_bytes = len(msg_json).to_bytes(4, byteorder=byte_order)

        try:
            stdout, stderr = process.communicate(input=length_bytes + msg_json, timeout=15)
            
            # Parse Response
            # Stdout: Length (4 bytes) + JSON
            if len(stdout) > 4:
                resp_len = int.from_bytes(stdout[:4], byteorder=byte_order)
                resp_json = stdout[4:4+resp_len].decode('utf-8')
                data = json.loads(resp_json)
                
                print("\n\n✨ ANSWER:")
                print(f"\"{data.get('answer', 'NO ANSWER FOUND')}\"")
                
                if "error" in data:
                    print(f"❌ Error: {data['error']}")
            else:
                print("\n❌ No response received.")
                print(f"Stderr: {stderr.decode('utf-8')}")

        except Exception as e:
            print(f"\n❌ Exception: {e}")
            if stderr:
                print(f"Stderr: {stderr.decode('utf-8')}")
                
        print("-" * 60)

if __name__ == "__main__":
    # Check if folder_reader.py exists
    if not os.path.exists(HOST_SCRIPT):
        print(f"Error: {HOST_SCRIPT} not found.")
    else:
        run_test()
