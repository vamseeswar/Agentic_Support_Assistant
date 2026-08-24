import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Application settings and configuration."""
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "Trendly Agentic Support Assistant"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # LLM Settings — supports "groq", "gemini", or "mock"
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "qwen/qwen3.6-27b"
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # Data file paths
    DATA_DIR: Path = BASE_DIR / "app" / "data"
    ORDERS_FILE: Path = BASE_DIR / "app" / "data" / "orders.json"
    POLICY_FILE: Path = BASE_DIR / "app" / "data" / "trendly_policy.md"

    # Evaluation / System Reference Date
    REFERENCE_DATE: str = "2026-08-01"

settings = Settings()
