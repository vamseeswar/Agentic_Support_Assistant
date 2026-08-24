import logging
from app.config import settings
from app.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


def create_llm_client() -> BaseLLMClient:
    """Factory: create the appropriate LLM client based on settings."""
    provider = settings.LLM_PROVIDER.lower().strip()

    if provider == "groq":
        from app.llm.groq_client import GroqClient
        logger.info("Using Groq LLM provider")
        return GroqClient()

    elif provider == "gemini":
        from app.llm.gemini_client import GeminiClient
        logger.info("Using Gemini LLM provider")
        return GeminiClient()

    elif provider == "mock":
        from app.llm.fallback_client import FallbackClient
        logger.info("Using Mock/Fallback LLM provider (no API key needed)")
        return FallbackClient()

    else:
        logger.warning(f"Unknown LLM_PROVIDER '{provider}', falling back to mock client.")
        from app.llm.fallback_client import FallbackClient
        return FallbackClient()
