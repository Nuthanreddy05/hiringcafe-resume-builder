import os
import time
import json
import logging
import requests
from collections import deque
from typing import List, Optional
from openai import OpenAI

# Simulating a logger for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AISelector")

class HeuristicSelector:
    """Backup Brain: Rule-based logic for when AI fails."""
    
    def select(self, question: str, options: List[str], profile: dict) -> str:
        q_lower = question.lower()
        
        # 1. Gender
        if 'gender' in q_lower:
            gender = profile.get('gender', 'Male').lower()
            # Try Exact/Start Match first (Avoid "Male" matching "Female")
            for opt in options:
                opt_lower = opt.lower()
                if opt_lower == gender: return opt
                if opt_lower.startswith(gender): return opt
                # Special case: "Man" matches "Male"
                if gender == "male" and opt_lower == "man": return opt
                if gender == "female" and opt_lower == "woman": return opt
        
        # 2. Race / Ethnicity
        if 'race' in q_lower or 'ethnicity' in q_lower:
             race = profile.get('demographics', {}).get('race', 'Asian').lower()
             for opt in options:
                 if race in opt.lower(): return opt
        
        # 3. Veteran Status
        if 'veteran' in q_lower:
             status = profile.get('demographics', {}).get('veteran', 'I am not').lower()
             is_not_veteran = 'not' in status or 'no' in status or 'non' in status
             
             for opt in options:
                 opt_lower = opt.lower()
                 if is_not_veteran:
                     if 'no' in opt_lower or 'not' in opt_lower: return opt
                 else:
                     # Is a veteran
                     if 'i am a' in opt_lower and 'not' not in opt_lower: return opt
                     if 'identify as one' in opt_lower: return opt
                 
        # 4. Disability
        if 'disability' in q_lower:
             status = profile.get('demographics', {}).get('disability', 'No').lower()
             is_no_disability = 'no' in status or "don't" in status
             
             for opt in options:
                 opt_lower = opt.lower()
                 if is_no_disability:
                     if 'no' in opt_lower or "don't" in opt_lower: return opt
                 else:
                     if 'yes' in opt_lower: return opt
        
        # 5. Sponsorship / Authorization
        if 'authorized' in q_lower: 
             for opt in options:
                 if 'yes' in opt.lower(): return opt
        if 'sponsorship' in q_lower or 'visa' in q_lower:
             # Default: "No" to requiring sponsorship
             target_req = False 
             # Logic: "Will you require?" -> No. "Do you NOT require?" -> Yes.
             # This is complex. Stick to simple heuristic:
             # If "require" in question -> No
             
             target = 'No'
             if 'not' in q_lower: target = 'Yes' # Negated question
             
             for opt in options:
                 if target.lower() == opt.lower(): return opt
                 if target.lower() in opt.lower(): return opt

        # 6. Source
        if 'hear' in q_lower:
             for opt in options:
                 if 'linkedin' in opt.lower(): return opt
        
        # Default: First option (Risky, but better than crash)
        logger.warning(f"Heuristic fallback used default for: {question}")
        return options[0]

class RateLimiter:
    """Prevents IP bans by tracking API calls."""
    def __init__(self, max_calls=50, window_seconds=60):
        self.calls = deque()
        self.max_calls = max_calls
        self.window = window_seconds
        
    def wait_if_needed(self):
        now = time.time()
        # Remove old calls
        while self.calls and self.calls[0] < now - self.window:
            self.calls.popleft()
            
        if len(self.calls) >= self.max_calls:
            sleep_time = self.window - (now - self.calls[0]) + 1
            logger.warning(f"Rate limit hit. Sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
            
        self.calls.append(time.time())

class AISelector:
    """
    Intelligent options selector using DeepSeek with fallback.
    Architectural Pattern: Circuit Breaker
    """
    def __init__(self):
        # Load .env manually
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, val = line.strip().split("=", 1)
                        os.environ[key] = val.strip("'").strip('"')

        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.fallback = HeuristicSelector()
        self.limiter = RateLimiter()
        self.cache = {} # Simple in-memory cache
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
        else:
            logger.warning("DEEPSEEK_API_KEY not set. Running in Heuristic-Only mode.")
            self.client = None

    def select_option(self, question: str, options: List[str], profile: dict) -> str:
        """
        Selects the best option from the list.
        Priority: Cache -> AI -> Heuristic
        """
        # 1. Check Cache
        cache_key = f"{question}|{','.join(options)}"
        if cache_key in self.cache:
            # logger.info("Cache hit")
            return self.cache[cache_key]
            
        # 2. Try AI (if configured)
        if self.client:
            self.limiter.wait_if_needed()
            try:
                prompt = f"""
                You are filling a job query. Select the EXACT text of the option that best matches the Profile.
                
                Question: "{question}"
                Options: {json.dumps(options)}
                
                Profile:
                {json.dumps(profile, indent=2)}
                
                INSTRUCTIONS:
                - Return ONLY the exact string from Options.
                - No explanation.
                - If strictly nothing matches, pick the most neutral/logical one.
                """
                
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    stream=False,
                    timeout=5 # 5s timeout
                )
                
                answer = response.choices[0].message.content.strip()
                
                # Cleanup quotes if AI adds them
                if answer.startswith('"') and answer.endswith('"'):
                    answer = answer[1:-1]
                
                # Validation: Verify answer is in options
                # 1. Exact Match
                if answer in options:
                    self.cache[cache_key] = answer
                    return answer
                
                # 2. Case-insensitive Match
                for opt in options:
                    if answer.lower() == opt.lower():
                        self.cache[cache_key] = opt
                        return opt
                        
                # 3. Fuzzy/Startswith Match (Strict)
                for opt in options:
                     if opt.lower().startswith(answer.lower()) or answer.lower().startswith(opt.lower()):
                         self.cache[cache_key] = opt
                         return opt

                logger.error(f"AI Invalid Answer: '{answer}' not in options {options}. Falling back.")
                
            except Exception as e:
                logger.warning(f"AI Fallback triggered: {e}")
                # Fall through to heuristic
        
        # 3. Fallback to Heuristics
        return self.fallback.select(question, options, profile)

    def generate_answer(self, question: str, profile: dict, job_context: dict = None) -> str:
        """
        Generates a free-text answer using Groq (Llama-3.3-70b).
        """
        # 1. Fallback Heuristics
        q_lower = question.lower()
        if "interested" in q_lower or "why" in q_lower:
            val = profile.get("why_interested")
            if val and not job_context: return val # Only use static if no context
        if "relative" in q_lower:
             val = profile.get("relatives_at_company")
             if val: return val
        if "linkedin" in q_lower:
             val = profile.get("linkedin")
             if val: return val
        if "website" in q_lower:
             val = profile.get("linkedin")
             if val: return val

        # 2. Try Groq API
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
             self.limiter.wait_if_needed()
             try:
                 url = "https://api.groq.com/openai/v1/chat/completions"
                 headers = {
                     "Authorization": f"Bearer {groq_key}",
                     "Content-Type": "application/json"
                 }
                 
                 # Enrich Context
                 context_str = ""
                 if job_context:
                     context_str = f"""
                     Job Context:
                     - Company: {job_context.get('company', 'Unknown')}
                     - Role: {job_context.get('title', 'Unknown')}
                     - Description Snippet: {job_context.get('description', '')[:1000]}...
                     """
                 
                 prompt = f"""
                 {context_str}
                 
                 Candidate Profile:
                 {json.dumps(profile, indent=2)}
                 
                 Question: "{question}"
                 
                 INSTRUCTIONS:
                 - Write a concise, professional answer (2-3 sentences).
                 - Use the First Person ("I").
                 - Mention the Company and Role specifically if available.
                 - Connect candidate experience to the Job Description.
                 - Do NOT use generic buzzwords ("leverages", "cutting-edge").
                 """
                 
                 payload = {
                     "model": "llama-3.3-70b-versatile",
                     "messages": [{"role": "user", "content": prompt}],
                     "max_tokens": 150,
                     "temperature": 0.7
                 }
                 
                 response = requests.post(url, headers=headers, json=payload, timeout=5)
                 
                 if response.status_code == 200:
                     return response.json()['choices'][0]['message']['content'].strip()
                 else:
                     logger.warning(f"Groq API Error {response.status_code}: {response.text}")
                     
             except Exception as e:
                 logger.warning(f"Groq Generation failed: {e}")
        
        # 3. Last Resort
        return ""

if __name__ == "__main__":
    # Test Stub
    print("🧪 Testing AISelector (Heuristic Mode if Key missing)...")
    
    selector = AISelector()
    profile = {
        "gender": "Male",
        "demographics": {"race": "Asian", "veteran": "No"}
    }
    
    # Test 1: Gender (Easy)
    opts = ["Female", "Male", "Non-binary"]
    ans = selector.select_option("Gender", opts, profile)
    print(f"Gender: {ans}")
    
    # Test 2: Veteran (Phrasing mismatch)
    opts = ["I am a protected veteran", "I am not a protected veteran", "Prefer not to say"]
    ans = selector.select_option("Veteran Status", opts, profile)
    print(f"Veteran: {ans}")
    
    # Test 3: AI Generation (Requires Key)
    print("Test 3: AI Generation")
    ans = selector.generate_answer("Why are you a good fit for this role?", profile)
    print(f"AI Answer: {ans}")

    if selector.client:
        print("✅ AI Client Initialized")
    else:
        print("❌ AI Client NOT Initialized")
