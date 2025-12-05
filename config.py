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
    
    # Gemini API
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
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
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in environment variables")
        
        required_db_keys = ['host', 'database', 'user', 'password', 'port']
        for key in required_db_keys:
            if not cls.DB_CONFIG.get(key):
                raise ValueError(f"Database configuration '{key}' is not set")
        
        return True
    
    @classmethod
    def get_db_config(cls) -> Dict[str, str]:
        """Get database configuration dictionary."""
        return cls.DB_CONFIG.copy()
