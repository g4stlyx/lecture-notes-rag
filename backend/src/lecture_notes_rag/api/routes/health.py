from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from lecture_notes_rag.api.dependencies import app_settings
from lecture_notes_rag.core.settings import Settings
from lecture_notes_rag.domain.schemas import HealthResponse
from lecture_notes_rag.persistence.database import get_session

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(
    session: Session = Depends(get_session),
    settings: Settings = Depends(app_settings),
) -> HealthResponse:
    database_ready = True
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        database_ready = False
    return HealthResponse(
        status="ok" if database_ready else "degraded",
        database_ready=database_ready,
        gemini_configured=bool(settings.gemini_api_key),
    )
