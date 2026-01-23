import os
import requests
import json
import time
from bs4 import BeautifulSoup

def scrape_with_ai(url, company_name):
    """
    Uses Groq (Llama-3) to parse job listings from raw HTML text.
    Returns a list of dicts: [{'title':..., 'url':..., 'date':..., 'location':...}]
    """
    # Load from .env if needed
    if not os.environ.get("GROQ_API_KEY"):
        try:
            with open(".env", "r") as f:
                for line in f:
                    if line.startswith("GROQ_API_KEY="):
                        os.environ["GROQ_API_KEY"] = line.strip().split("=", 1)[1].strip("'\"")
                        break
        except:
            pass

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("  ❌ GROQ_API_KEY not found. Skipping AI scrape.")
        return []

    print(f"  🧠 AI Scraping {company_name} - {url}...")
    
    try:
        # 1. Fetch Page with Playwright (to handle JS)
        from playwright.sync_api import sync_playwright
        
        text_content = ""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                # Block resources to speed up
                page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())
                
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000) # Wait for hydration
                
                # Get text with links formatted as Markdown [Request](URL)
                # This ensures the LLM sees the URLs associated with the job titles
                script = """
                (() => {
                    Array.from(document.querySelectorAll('a')).forEach(a => {
                        if (a.innerText.trim().length > 5) {
                            try {
                                let text = a.innerText.replace(/\\n/g, ' ');
                                a.innerText = ` [${text}](${a.href}) `;
                            } catch (e) {}
                        }
                    });
                    return document.body.innerText;
                })()
                """
                text_content = page.evaluate(script)
                browser.close()
        except Exception as pe:
             print(f"  ⚠️ Playwright failed, falling back to Requests: {pe}")
             resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
             soup = BeautifulSoup(resp.text, 'html.parser')
             text_content = soup.get_text(separator=' ', strip=True)

        # Truncate for token limit (approx 15k chars is safe for Llama-3 70b context)
        text_content = text_content[:15000].replace("\n", " ")
        
        # 3. Prompt Groq
        prompt = f"""
        You are a high-precision Job Scraper.
        Extract strictly valid JOB POSTINGS from the text below from the company "{company_name}".
        
        RULES:
        1. Ignore articles, blogs, surveys, reports, or general info. ONLY extract open roles.
        2. Extracted URL must be a valid link pattern if visible, or "Unknown".
        3. Output valid JSON list of objects: {{"title": "...", "url": "...", "date": "YYYY-MM-DD", "location": "..."}}
        4. If date is not found, use "Unknown". 
        5. Return ONLY the JSON. No markdown formatting.
        
        TEXT CONTENT:
        {text_content}
        """
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1 # Low temp for precision
        }
        
        g_resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=15
        )
        
        if g_resp.status_code != 200:
            print(f"  ❌ Groq Error: {g_resp.text}")
            return []
            
        content = g_resp.json()['choices'][0]['message']['content']
        
        # Clean potential markdown
        content = content.replace("```json", "").replace("```", "").strip()
        
        jobs = json.loads(content)
        print(f"  ✅ AI Found {len(jobs)} potential jobs.")
        return jobs

    except Exception as e:
        print(f"  ❌ AI Scrape Failed: {e}")
        return []
