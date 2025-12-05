"""
LLM Service - Unified interface for Gemini and OpenAI
Handles API calls to different AI providers with consistent interface
"""

import google.generativeai as genai
from openai import OpenAI
from config import Config


class LLMService:
    """
    Unified LLM service supporting multiple AI providers.
    Provides consistent interface regardless of underlying provider.
    """
    
    def __init__(self):
        """Initialize the LLM service based on configured provider."""
        self.provider = Config.AI_PROVIDER
        
        if self.provider == 'gemini':
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.model_name = "gemini-2.0-flash-exp"
        elif self.provider == 'openai':
            self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
            self.model_name = Config.OPENAI_MODEL
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
    
    def generate_content(self, prompt: str) -> str:
        """
        Generate content using the configured AI provider.
        
        Args:
            prompt: The prompt to send to the AI
            
        Returns:
            Generated text response
        """
        if self.provider == 'gemini':
            return self._generate_gemini(prompt)
        elif self.provider == 'openai':
            return self._generate_openai(prompt)
    
    def _generate_gemini(self, prompt: str) -> str:
        """Generate content using Gemini API."""
        try:
            model = genai.GenerativeModel(self.model_name)
            resp = model.generate_content(prompt)
            
            # Safe text extraction for Gemini
            if (
                resp and resp.candidates and
                resp.candidates[0].content and
                resp.candidates[0].content.parts
            ):
                return resp.text.strip()
            return None
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    def _generate_openai(self, prompt: str) -> str:
        """Generate content using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are John, an expert AI database assistant built by imsrj. You help users query and understand their database in natural language."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent SQL generation
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def get_provider_name(self) -> str:
        """Get the name of the current provider."""
        return self.provider.title()
    
    def get_model_name(self) -> str:
        """Get the name of the current model."""
        return self.model_name


# Initialize global LLM service instance
def get_llm_service() -> LLMService:
    """Get or create LLM service instance."""
    return LLMService()
