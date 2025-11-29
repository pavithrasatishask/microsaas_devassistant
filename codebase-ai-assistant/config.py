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
    
    # PDF Processing Configuration
    PDF_STORAGE_PATH = os.getenv("PDF_STORAGE_PATH", "/tmp/documents")
    MAX_PDF_SIZE_MB = 50  # Max PDF file size in MB
    MAX_PDF_PAGES = 500   # Max pages per PDF
    PDF_TEXT_CHUNK_SIZE = 2000  # Tokens per chunk for large PDFs
    
    # Supabase Storage (optional, for future use)
    SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "repository-documents")

