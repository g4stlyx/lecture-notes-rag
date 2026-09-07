from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import update

from lecture_notes_rag.persistence.database import SessionLocal
from lecture_notes_rag.persistence.models import IngestionJob

logger = logging.getLogger(__name__)


def recover_interrupted_ingestion_jobs() -> int:
    """Release local jobs whose in-process FastAPI worker died during shutdown."""
    with SessionLocal() as session:
        result = session.execute(
            update(IngestionJob)
            .where(IngestionJob.status.in_(["queued", "running"]))
            .values(
                status="interrupted",
                completed_at=datetime.now(UTC),
                error_summary=(
                    "The local server stopped before this in-process ingestion job finished. "
                    "Start a new job to resume; ready documents will be skipped."
                ),
            )
        )
        session.commit()
    recovered = result.rowcount or 0
    if recovered:
        logger.warning("Recovered %s interrupted ingestion job(s)", recovered)
    return recovered
