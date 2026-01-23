import os
import json
from typing import Optional, Dict, List, Any, Union
from openai import OpenAI
from google import genai
from google.genai import types
from pathlib import Path

class LLMClient:
    """
    Unified client for interacting with DeepSeek (via OpenAI SDK) and Google Gemini.
    """
    
    def __init__(self):
        # 1. Try Environment Variables First
        self.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        
        # 2. Try credentials.yaml Fallback
        if not (self.deepseek_api_key and self.gemini_api_key):
             try:
                 import yaml
                 config_path = Path("job_automation/config/credentials.yaml")
                 if config_path.exists():
                     conf = yaml.safe_load(config_path.read_text())
                     llm_conf = conf.get('llm', {})
                     if not self.deepseek_api_key:
                         self.deepseek_api_key = llm_conf.get('deepseek_key')
                     if not self.gemini_api_key:
                         self.gemini_api_key = llm_conf.get('gemini_key')
             except Exception as e:
                 print(f"⚠️ Failed to read credentials.yaml for LLM keys: {e}")

        # DeepSeek Configuration
        self.deepseek_model = "deepseek-chat"
        self.deepseek_client = None
        
        if self.deepseek_api_key:
            self.deepseek_client = OpenAI(
                api_key=self.deepseek_api_key,
                base_url="https://api.deepseek.com"
            )
            
        # Gemini Configuration
        self.gemini_model = "gemini-2.0-flash-exp" 
        self.gemini_client = None
        
        if self.gemini_api_key:
            self.gemini_client = genai.Client(api_key=self.gemini_api_key)

    def generate_text(self, 
                     provider: str, 
                     prompt: str, 
                     system_prompt: str = "You are a helpful assistant.",
                     model: Optional[str] = None,
                     temperature: float = 0.7) -> str:
        """
        Generate plain text response.
        """
        if provider.lower() == "deepseek":
            return self._generate_deepseek(prompt, system_prompt, model, temperature, json_mode=False)
        elif provider.lower() == "gemini":
            return self._generate_gemini(prompt, system_prompt, model, temperature, json_mode=False)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def generate_json(self, 
                     provider: str, 
                     prompt: str, 
                     system_prompt: str = "You are a JSON generator. Return only valid JSON.",
                     model: Optional[str] = None,
                     temperature: float = 0.7) -> Any:
        """
        Generate and parse JSON response.
        """
        if provider.lower() == "deepseek":
            content = self._generate_deepseek(prompt, system_prompt, model, temperature, json_mode=True)
        elif provider.lower() == "gemini":
            content = self._generate_gemini(prompt, system_prompt, model, temperature, json_mode=True)
        else:
            raise ValueError(f"Unknown provider: {provider}")
            
        # Parse JSON
        try:
            # Clean markdown code blocks if present
            if "```" in content:
                import re
                content = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", content, flags=re.DOTALL | re.IGNORECASE)
            
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error ({provider}): {e}")
            print(f"   Content snippet: {content[:200]}...")
            return {}

    def _generate_deepseek(self, prompt: str, system_prompt: str, model: str, temperature: float, json_mode: bool) -> str:
        if not self.deepseek_client:
            raise RuntimeError("DeepSeek API key not found in env vars.")
            
        model = model or self.deepseek_model
        
        response_format = {"type": "json_object"} if json_mode else {"type": "text"}
        
        try:
            response = self.deepseek_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                response_format=response_format
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ DeepSeek API Error: {e}")
            raise

    def _generate_gemini(self, prompt: str, system_prompt: str, model: str, temperature: float, json_mode: bool) -> str:
        if not self.gemini_client:
            raise RuntimeError("Gemini API key not found in env vars.")
            
        model = model or self.gemini_model
        
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_prompt,
            response_mime_type="application/json" if json_mode else "text/plain"
        )
        
        try:
            response = self.gemini_client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            print(f"❌ Gemini API Error: {e}")
            raise
