"""
LLM Client
Handles communication with OpenAI, Anthropic LLMs, or Offline Template Engine.
Set LLM_PROVIDER=offline in .env to run with no API key.
"""
import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMClient:
    """Unified interface for LLM providers (openai | anthropic | offline)"""
    
    def __init__(self, provider: str = None):
        self.logger = logging.getLogger(__name__)
        self.provider = provider or os.getenv("LLM_PROVIDER", "offline")
        
        if self.provider == "openai":
            self._init_openai()
        elif self.provider == "anthropic":
            self._init_anthropic()
        elif self.provider == "offline":
            self._init_offline()
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}. Use: openai | anthropic | offline")
    
    def _init_openai(self):
        """Initialize OpenAI client (supports OpenAI, GitHub Copilot, Azure OpenAI)"""
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")

            # Optional: custom base URL for GitHub Copilot or Azure OpenAI
            base_url = os.getenv("OPENAI_BASE_URL", None)
            if base_url:
                self.client = OpenAI(api_key=api_key, base_url=base_url)
                self.logger.info(f"Using custom base URL: {base_url}")
            else:
                self.client = OpenAI(api_key=api_key)

            self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
            self.logger.info(f"Initialized OpenAI client with model: {self.model}")
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
    
    def _init_anthropic(self):
        """Initialize Anthropic client"""
        try:
            from anthropic import Anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
            
            self.client = Anthropic(api_key=api_key)
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
            self.logger.info(f"Initialized Anthropic client with model: {self.model}")
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
    
    def _init_offline(self):
        """Initialize offline template engine — no API key required"""
        from template_engine import TemplateEngine
        self.engine = TemplateEngine()
        self.logger.info("Initialized OFFLINE template engine (no API key required)")

    def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """Generate response from LLM or offline template engine"""
        try:
            if self.provider == "openai":
                return self._generate_openai(prompt, system_prompt, temperature, max_tokens)
            elif self.provider == "anthropic":
                return self._generate_anthropic(prompt, system_prompt, temperature, max_tokens)
            elif self.provider == "offline":
                return self.engine.generate(prompt, system_prompt)
        except Exception as e:
            self.logger.error(f"LLM generation failed: {str(e)}")
            raise
    
    def _generate_openai(self, prompt: str, system_prompt: Optional[str], temperature: float, max_tokens: int) -> str:
        """Generate using OpenAI"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def _generate_anthropic(self, prompt: str, system_prompt: Optional[str], temperature: float, max_tokens: int) -> str:
        """Generate using Anthropic"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt if system_prompt else "",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text
