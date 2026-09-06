from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from lecture_notes_rag.api.dependencies import require_gemini_provider
from lecture_notes_rag.domain.schemas import IngestionJobRequest, IngestionJobResponse
from lecture_notes_rag.generation.gemini import GeminiProvider
from lecture_notes_rag.persistence.database import get_session
from lecture_notes_rag.persistence.models import IngestionJob
from lecture_notes_rag.workers.ingestion_worker import run_ingestion_job

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/jobs", response_model=IngestionJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_ingestion_job(
    payload: IngestionJobRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    _: GeminiProvider = Depends(require_gemini_provider),
) -> IngestionJobResponse:
    running = session.scalar(
        select(IngestionJob).where(IngestionJob.status.in_(["queued", "running"]))
    )
    if running is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ingestion job {running.id} is already {running.status}.",
        )
    job = IngestionJob(force=payload.force)
    session.add(job)
    session.commit()
    session.refresh(job)
    background_tasks.add_task(run_ingestion_job, job.id)
    return _response(job)


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
def get_ingestion_job(job_id: str, session: Session = Depends(get_session)) -> IngestionJobResponse:
    try:
        from uuid import UUID

        parsed_id = UUID(job_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid job ID"
        ) from error
    job = session.get(IngestionJob, parsed_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion job not found")
    return _response(job)


def _response(job: IngestionJob) -> IngestionJobResponse:
    return IngestionJobResponse(
        id=job.id,
        status=job.status,
        discovered_count=job.discovered_count,
        processed_count=job.processed_count,
        skipped_count=job.skipped_count,
        failed_count=job.failed_count,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_summary=job.error_summary,
    )
