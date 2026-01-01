from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_URL: str = "postgresql://localhost:5432/postgres"
    REDIS_URL: str = "redis://localhost:6379"
    
    # Security
    SECRET_KEY: str = "default-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # OpenAI
    OPENAI_API_KEY: str = "sk-fake-openai-key"
    
    # Stripe
    STRIPE_SECRET_KEY: str = "sk_test_fake"
    STRIPE_PUBLISHABLE_KEY: str = "pk_test_fake"
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_ID_PRO: Optional[str] = None
    
    # QuickBooks
    QUICKBOOKS_CLIENT_ID: str = "fake_id"
    QUICKBOOKS_CLIENT_SECRET: str = "fake_secret"
    QUICKBOOKS_REDIRECT_URI: str = "https://example.com/callback"
    QUICKBOOKS_ENVIRONMENT: str = "sandbox"
    
    # Email (Optional)
    RESEND_API_KEY: Optional[str] = None
    
    # Storage
    S3_BUCKET_NAME: str = "finflow-documents"
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None
    S3_REGION: str = "auto"
    
    # App
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    ENVIRONMENT: str = "development"
    
    # Usage limits
    FREE_TIER_PAGES_PER_MONTH: int = 100
    PRO_TIER_PAGES_PER_YEAR: int = 7500
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance - will use defaults if env vars not set
settings = Settings()
