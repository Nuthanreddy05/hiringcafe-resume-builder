#!/usr/bin/env python3
"""
Native messaging host to read job folders.
Receives: {"action": "get_jobs", "base_path": "optional/path"}
Returns: {"jobs": [{"company": "...", "job_title": "...", ...}]}
"""

import sys
import json
import os
import glob
from pathlib import Path
from datetime import datetime

# Debug Logging
# Debug Logging
# Debug Logging
LOG_FILE = "/tmp/smartjob_debug.log"

def log(msg):
    # Ensure directory exists just in case
    # os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()}: {msg}\n")
        f.flush()

def get_message():
    """Read message from Chrome extension using Native Messaging protocol."""
    try:
        # Read the message length (first 4 bytes)
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length:
            log("Read 0 bytes (EOF)")
            return None
        
        message_length = int.from_bytes(raw_length, byteorder=sys.byteorder)
        log(f"Message length: {message_length}")
        
        # Read the message content
        message = sys.stdin.buffer.read(message_length).decode('utf-8')
        log(f"Received message: {message}")
        return json.loads(message)
    except Exception as e:
        log(f"Error reading message: {e}")
        # Log error to stderr (Native Messaging stdout is reserved)
        sys.stderr.write(f"Error reading message: {e}\n")
        return None

def send_message(message):
    """Send message to Chrome extension using Native Messaging protocol."""
    try:
        log(f"Sending message: {json.dumps(message)[:50]}...")
        encoded_message = json.dumps(message).encode('utf-8')
        sys.stdout.buffer.write(len(encoded_message).to_bytes(4, byteorder=sys.byteorder))
        sys.stdout.buffer.write(encoded_message)
        sys.stdout.buffer.flush()
    except Exception as e:
         log(f"Error sending message: {e}")
         sys.stderr.write(f"Error sending message: {e}\n")

def get_job_status(folder_path):
    """Read .status.json if it exists."""
    status_path = os.path.join(folder_path, ".status.json")
    if os.path.exists(status_path):
        try:
            with open(status_path, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def _detect_platform(url):
    """Detect ATS platform from URL."""
    if not url:
        return "generic"
    url = url.lower()
    if "greenhouse.io" in url:
        return "greenhouse"
    if "lever.co" in url:
        return "lever"
    if "myworkdayjobs.com" in url:
        return "workday"
    if "taleo.net" in url:
        return "taleo"
    if "smartrecruiters.com" in url:
        return "smartrecruiters"
    if "ashbyhq.com" in url:
        return "ashby"
    return "generic"

def read_job_folders(base_path_str):
    """Read all job folders from the specified directory."""
    jobs = []
    
    # Resolve ~ to user home
    base_path = os.path.expanduser(base_path_str)
    
    if not os.path.exists(base_path):
        return {"error": f"Path not found: {base_path}"}
    
    # Iterate through folders
    try:
        entries = os.listdir(base_path)
    except Exception as e:
        return {"error": f"Failed to list directory: {e}"}

    for folder_name in entries:
        folder_path = os.path.join(base_path, folder_name)
        
        if not os.path.isdir(folder_path):
            continue
            
        # Skip hidden/system folders
        if folder_name.startswith('.'):
            continue
        
        meta_path = os.path.join(folder_path, "meta.json")
        resume_path = os.path.join(folder_path, "NuthanReddy.pdf")
        cover_letter_path = os.path.join(folder_path, "cover_letter.txt")
        
        # We need meta.json to identify a valid job folder
        if not os.path.exists(meta_path):
            continue
        
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            # Get folder creation/modification time
            stats = os.stat(folder_path)
            created_at_ts = stats.st_mtime
            
            # Check for existing status
            status_data = get_job_status(folder_path)
            current_status = status_data.get("status", "pending")
            
            # Platform Detection
            apply_url = meta.get("apply_url", meta.get("job_url", ""))
            platform = _detect_platform(apply_url)
            
            jobs.append({
                "company": meta.get("company", "Unknown"),
                "job_title": meta.get("title", meta.get("job_title", "Unknown")), # Map 'title' correctly
                "job_url": meta.get("job_url", ""),
                "apply_url": apply_url,
                "platform": platform, # Use detected platform
                "resume_path": resume_path if os.path.exists(resume_path) else None,
                "cover_letter_path": cover_letter_path if os.path.exists(cover_letter_path) else None,
                "folder_path": folder_path,
                "created_at": datetime.fromtimestamp(created_at_ts).isoformat(),
                "created_ts": created_at_ts, # For sorting
                "status": current_status
            })
        except Exception as e:
            sys.stderr.write(f"Error parsing folder {folder_name}: {e}\n")
            continue
    
    # Sort by created_at timestamp (Newest First) - Standard
    jobs.sort(key=lambda x: x['created_ts'], reverse=True)
    
    # Remove raw timestamp before sending
    for job in jobs:
        del job['created_ts']
        
    return {"jobs": jobs}

# Aliases for compatibility with handle_message
get_jobs = read_job_folders

def save_job_status(data):
    """Update .status.json for a job."""
    folder_path = data.get("folder_path")
    status = data.get("status")
    
    if not folder_path or not os.path.exists(folder_path):
        return {"error": "Invalid folder path"}
        
    status_file = os.path.join(folder_path, ".status.json")
    
    try:
        content = {
            "status": status,
            "updated_at": datetime.now().isoformat(),
            "method": "extension"
        }
        with open(status_file, 'w') as f:
            json.dump(content, f, indent=2)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

# Alias for compatibility
update_job_status = save_job_status

def handle_message(message):
    """Handle incoming messages from the extension."""
    action = message.get("action")
    log(f"DEBUG: Running from {__file__}")
    log(f"DEBUG: Handling action: {repr(action)}")
    
    try:
        if action == "get_jobs":
            # Default to Desktop/Google Auto if no path provided
            base_path = message.get("base_path", "/Users/nuthanreddyvaddireddy/Desktop/Google Auto")
            return get_jobs(base_path)
            
        elif action == "update_status":
            return update_job_status(message)
            
        elif action == "generate_answer":
            return generate_ai_answer(message)

        elif action == "generate_cover_letter":
            return generate_cover_letter_func(message)

        elif action == "upload_file":
            log("📂 Upload: Starting file upload automation...")
            try:
                file_path = message.get("file_path", "")
                
                if not file_path:
                    return {"success": False, "error": "No file path provided"}
                
                # Call upload automation script
                import subprocess
                
                # Verify script is in the same directory (safe for both dev and install)
                script_path = os.path.join(
                    os.path.dirname(__file__), 
                    'upload_automation.py'
                )
                
                # Run it
                result = subprocess.run(
                    ['python3', script_path, file_path],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if result.returncode == 0:
                    log("✅ Upload: File uploaded successfully")
                    return {"success": True}
                else:
                    log(f"❌ Upload Failed: {result.stderr}")
                    return {"success": False, "error": result.stderr}
                    
            except Exception as e:
                log(f"❌ Upload Exception: {e}")
                return {"success": False, "error": str(e)}
            
        elif action == "ping":
            return {"status": "ok", "version": "1.0.0"}
            
        else:
            return {"error": f"Unknown action: {action}"}
            
    except Exception as e:
        log(f"Error handling message: {e}")
        return {"error": str(e)}

# --- AI Question Answering ---

def load_environment_variable(key):
    """Load variable from .env file in parent directory."""
    try:
        # Assuming .env is in the project root (up 3 levels from here: .../chrome-extension/native-messaging/folder_reader.py)
        # Actually, script is in chrome-extension/native-messaging/
        # Root is ../../
        
        # Try multiple locations
        possible_paths = [
            Path(__file__).parent.parent.parent / ".env",  # Root
            Path.home() / "Desktop" / "CERTIFICATES" / "google" / ".env",
            Path.cwd() / ".env"
        ]
        
        for env_path in possible_paths:
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith(f"{key}=") or line.startswith(f"export {key}="):
                            value = line.split("=", 1)[1].strip("'\"")
                            return value
    except Exception as e:
        log(f"Error loading .env: {e}")
    return None


def find_job_folder_by_url(target_url, base_path):
    """Scan all folders to find one matching the URL."""
    if not target_url:
        return None
        
    try:
        # Normalize target
        target_clean = target_url.split('?')[0].rstrip('/')
        
        entries = os.listdir(base_path)
        for folder_name in entries:
            folder_path = os.path.join(base_path, folder_name)
            meta_path = os.path.join(folder_path, "meta.json")
            
            if os.path.isdir(folder_path) and os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r') as f:
                        meta = json.load(f)
                    
                    job_url = meta.get("job_url", "")
                    apply_url = meta.get("apply_url", "")
                    
                    # Check match
                    if (job_url and target_clean in job_url) or (apply_url and target_clean in apply_url):
                        return folder_path
                except:
                    continue
    except Exception as e:
        log(f"Error searching folders: {e}")
        
    return None

def generate_ai_answer(message):
    """Generate answer using Groq API."""
    import requests
    
    question = message.get("question")
    context = message.get("context", {})
    job_folder_id = message.get("job_folder_id") 
    
    if not question:
        return {"error": "No question provided"}

    # 1. Load Resume Context
    resume_text = message.get("resume_text", "")
    
    if not resume_text:
        try:
            # Find job folder
            base_path = Path("/Users/nuthanreddyvaddireddy/Desktop/Google Auto")
            job_path = None
            
            if job_folder_id and job_folder_id != "LATEST":
                 job_path = base_path / job_folder_id
            
            # If no ID, try to find by URL from context
            if not job_path and context.get("url"):
                found_path = find_job_folder_by_url(context["url"], str(base_path))
                if found_path:
                    job_path = Path(found_path)
                    log(f"Matched Job by URL: {job_path.name}")
                
            if job_path:
                # Try meta.json
                meta_path = job_path / "meta.json"
                if meta_path.exists():
                    with open(meta_path) as f:
                        meta = json.load(f)
                        # Use resume summary or extracted text if available
                        resume_text = meta.get("resume_text", "")
                        if not resume_text and "summary" in meta:
                            resume_text = f"Summary: {meta['summary']}\nExperience: {meta.get('experience', [])}"
            
            if not resume_text:
                 # Fallback to User's Real Resume
                 resume_text = """
NUTHAN REDDY VADDI REDDY
nuthanreddy001@gmail.com | +1682-406-56-46 | github.com/Nuthanreddy05
Data Analyst with 4+ years of experience specializing in business intelligence solutions using SQL, Python, and Looker.
Experience:
Data Analyst, Albertsons - Dallas, TX (May 2024 - Present):
- Analyzing churn patterns across 2M subscriber accounts using survival analysis in Python.
- Developing automated pipelines maximizing 25% reduction in report time.
- Inventory demand forecasting using AWS Sagemaker (15-20% accuracy improvement).
- Optimizing Snowflake queries reducing execution time from 45 to 32 seconds.
- Collaborating on Kafka streams processing 20k events/sec.

Data Analyst, ValueLabs - Hyderabad (May 2020 - July 2023):
- Built SQL reports for 1TB monthly data, improving efficiency by 20%.
- Python scripts for data extraction improving efficiency by 24%.
- Visualization prototypes in Tableau for 50k MAUs.
- Optimized queries reducing execution time by 26% handling 100M records.

Education:
MS in Data Science, University of Texas at Arlington (3.8 GPA).
Skills: Python, SQL, Looker, Tableau, AWS Sagemaker, Snowflake, Kafka.
"""
                 
        except Exception as e:
            log(f"Error loading resume context: {e}")
            resume_text = "Experienced Professional"

    # 2. Get API Key
    api_key = load_environment_variable("GROQ_API_KEY")
    if not api_key:
        return {"error": "GROQ_API_KEY not found in .env"}


    # 3. Prepare Prompt
    job_title = context.get("jobTitle", "a role")
    company = context.get("company", "a company")
    
    system_prompt = "You are a professional career coach, helping candidates answer screening questions concisely and effectively."
    user_prompt = f"""
Candidate Background:
{resume_text[:2000]}
    
Job Context:
Role: {job_title} at {company}
    
Screening Question:
"{question}"
    
Answer:
"""
    
    # Call Groq (Same Logic)
    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 300 
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            return {"answer": data['choices'][0]['message']['content'].strip()}
        else:
            return {"error": f"Groq Error: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

def generate_cover_letter_func(message):
    """Generate a cover letter."""
    import requests
    
    context = message.get("context", {})
    # 1. Load context + Resume (Same as Answer)
    # Re-use logic or just duplicate for safety
    resume_text = message.get("resume_text", "")
    if not resume_text:
         # Fallback logic (Duplicated for simplicity to avoid refactoring risk)
         try:
            base_path = Path("/Users/nuthanreddyvaddireddy/Desktop/Google Auto")
            job_folder_id = message.get("job_folder_id")
            job_path = None
            if job_folder_id and job_folder_id != "LATEST":
                 job_path = base_path / job_folder_id
            if not job_path and context.get("url"):
                found_path = find_job_folder_by_url(context["url"], str(base_path))
                if found_path: job_path = Path(found_path)
            
            if job_path:
                meta_path = job_path / "meta.json"
                if meta_path.exists():
                    with open(meta_path) as f:
                        meta = json.load(f)
                        resume_text = meta.get("resume_text", "")
            
            if not resume_text:
                 resume_text = """
NUTHAN REDDY VADDI REDDY
nuthanreddy001@gmail.com | +1682-406-56-46
Data Analyst with 4+ years of experience specializing in business intelligence solutions using SQL, Python, and Looker.
Experience: Albertsons (Data Analyst, 2024-Present), ValueLabs (Data Analyst, 2020-2023).
Skills: Python, SQL, Looker, Tableau, AWS Sagemaker, Snowflake, Kafka.
"""
         except:
             resume_text = "Experienced Data Professional."

    api_key = load_environment_variable("GROQ_API_KEY")
    if not api_key: return {"error": "GROQ_API_KEY Missing"}

    prompt = f"""You are Nuthan Reddy Vaddireddy. Write a professional Cover Letter for:
Role: {context.get('jobTitle', 'Data Analyst')}
Company: {context.get('company', 'the Hiring Team')}

RESUME:
{resume_text}

INSTRUCTIONS:
1. Keep it brief (3 paragraphs max).
2. Focus on "Why Me" (Match skills to role).
3. Professional tone.
4. Do NOT include [Placeholders]. Use "Hiring Manager" if name unknown.

COVER LETTER:"""

    try:
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}'},
            json={
                'model': 'llama-3.3-70b-versatile',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.7
            }
        )
        if response.status_code == 200:
            return {"answer": response.json()['choices'][0]['message']['content'].strip()}
        else:
            return {"error": response.text}
    except Exception as e:
        return {"error": str(e)}

def main():
    """Main message loop."""
    while True:
        try:
            message = get_message()
            if message is None:
                break
            
            response = handle_message(message)
            send_message(response)
                
        except BrokenPipeError:
            # SysLog check
            pass
        except Exception as e:
            log(f"Critical error in main loop: {e}")
            
if __name__ == "__main__":
    main()
