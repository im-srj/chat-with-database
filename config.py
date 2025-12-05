"""
Configuration management for AI Database Manager
Loads and validates environment variables
"""

import os
from dotenv import load_dotenv
from typing import Dict

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""
    
    # AI Provider Selection
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()  # 'gemini' or 'openai'
    
    # Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # OpenAI API
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # gpt-4o, gpt-4o-mini, gpt-4-turbo, etc.
    
    # Database Configuration
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'choithrams'),
        'user': os.getenv('DB_USER', 'imsrj'),
        'password': os.getenv('DB_PASSWORD', 'imhere'),
        'port': os.getenv('DB_PORT', '5432')
    }
    
    # Schema Settings
    SCHEMA_CACHE_DURATION_MINUTES = int(os.getenv('SCHEMA_CACHE_DURATION_MINUTES', '60'))
    
    # Application Settings
    APP_TITLE = os.getenv('APP_TITLE', 'AI Database Manager')
    MAX_MEMORY_ROUNDS = int(os.getenv('MAX_MEMORY_ROUNDS', '5'))
    
    # Query Settings
    MAX_RESULT_ROWS = int(os.getenv('MAX_RESULT_ROWS', '1000'))
    QUERY_TIMEOUT_SECONDS = int(os.getenv('QUERY_TIMEOUT_SECONDS', '30'))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration values."""
        # Validate AI provider
        if cls.AI_PROVIDER not in ['gemini', 'openai']:
            raise ValueError(f"AI_PROVIDER must be 'gemini' or 'openai', got: {cls.AI_PROVIDER}")
        
        # Validate API keys based on provider
        if cls.AI_PROVIDER == 'gemini' and not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set. Required when AI_PROVIDER=gemini")
        
        if cls.AI_PROVIDER == 'openai' and not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set. Required when AI_PROVIDER=openai")
        
        required_db_keys = ['host', 'database', 'user', 'password', 'port']
        for key in required_db_keys:
            if not cls.DB_CONFIG.get(key):
                raise ValueError(f"Database configuration '{key}' is not set")
        
        return True
    
    @classmethod
    def get_db_config(cls) -> Dict[str, str]:
        """Get database configuration dictionary."""
        return cls.DB_CONFIG.copy()
