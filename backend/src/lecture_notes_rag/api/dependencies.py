from __future__ import annotations

from fastapi import HTTPException, status

from lecture_notes_rag.core.settings import Settings, get_settings
from lecture_notes_rag.generation.gemini import GeminiConfigurationError, GeminiProvider


def require_gemini_provider() -> GeminiProvider:
    settings = get_settings()
    try:
        return GeminiProvider(settings)
    except GeminiConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini is not configured on the server.",
        ) from error


def app_settings() -> Settings:
    return get_settings()
