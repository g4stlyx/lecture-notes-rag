from __future__ import annotations

from uuid import UUID

from lecture_notes_rag.core.settings import get_settings
from lecture_notes_rag.generation.gemini import GeminiProvider
from lecture_notes_rag.persistence.database import SessionLocal
from lecture_notes_rag.services.ingestion import IngestionService


def run_ingestion_job(job_id: UUID) -> None:
    """FastAPI background-task entry point; uses a dedicated database session."""
    settings = get_settings()
    with SessionLocal() as session:
        provider = GeminiProvider(settings)
        IngestionService(session, provider, settings).run(job_id)
