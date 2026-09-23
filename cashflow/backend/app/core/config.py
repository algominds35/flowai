from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+psycopg2://cashflow:cashflow_secret@localhost:5432/cashflow_db"
    DATABASE_URL_ASYNC: Optional[str] = None

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production-please"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # App
    APP_NAME: str = "CashFlow"
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Plaid
    PLAID_CLIENT_ID: Optional[str] = None
    PLAID_SECRET: Optional[str] = None
    PLAID_ENV: str = "sandbox"  # sandbox | development | production

    # QuickBooks Online
    QBO_CLIENT_ID: Optional[str] = None
    QBO_CLIENT_SECRET: Optional[str] = None
    QBO_REDIRECT_URI: str = "http://localhost:8000/api/v1/integrations/qbo/callback"
    QBO_ENVIRONMENT: str = "sandbox"  # sandbox | production

    # Shopify
    SHOPIFY_API_KEY: Optional[str] = None
    SHOPIFY_API_SECRET: Optional[str] = None
    SHOPIFY_REDIRECT_URI: str = "http://localhost:8000/api/v1/integrations/shopify/callback"

    # Amazon Marketplace
    AMAZON_APP_ID: Optional[str] = None
    AMAZON_CLIENT_ID: Optional[str] = None
    AMAZON_CLIENT_SECRET: Optional[str] = None

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
