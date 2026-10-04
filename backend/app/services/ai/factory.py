from app.core.config import Settings, get_settings
from app.services.ai.base import AIService
from app.services.ai.gemini import GeminiAIService
from app.services.ai.mock import MockAIService


def get_ai_service(settings: Settings | None = None) -> AIService:
    settings = settings or get_settings()
    if settings.gemini_api_key.strip():
        return GeminiAIService(api_key=settings.gemini_api_key.strip())
    return MockAIService()
