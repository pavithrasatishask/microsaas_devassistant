"""Configuration settings for the CodeBase AI Assistant."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    
    # Anthropic Claude API
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL = "claude-haiku-4-20250514"  # Haiku 4.5 for cost efficiency
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Repository Storage
    REPOS_BASE_PATH = os.getenv("REPOS_BASE_PATH", "/tmp/repositories")
    
    # Flask Configuration
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    
    # Redis Configuration (optional)
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # API Limits
    MAX_TOKENS_PER_REQUEST = 4096
    MAX_REPO_SIZE_MB = 100

