from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lecture_notes_rag.api.dependencies import app_settings
from lecture_notes_rag.core.settings import Settings
from lecture_notes_rag.domain.schemas import DocumentDetail, DocumentListResponse, DocumentSummary
from lecture_notes_rag.persistence.database import get_session
from lecture_notes_rag.persistence.models import Document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
def list_documents(
    semester: int | None = Query(default=None, ge=1, le=8),
    course: str | None = Query(default=None, max_length=160),
    document_status: str | None = Query(default=None, alias="status", max_length=32),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    session: Session = Depends(get_session),
) -> DocumentListResponse:
    query = select(Document)
    count_query = select(func.count()).select_from(Document)
    for criterion in _filters(semester, course, document_status):
        query = query.where(criterion)
        count_query = count_query.where(criterion)
    documents = session.scalars(
        query.order_by(Document.semester, Document.course, Document.display_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    total = session.scalar(count_query) or 0
    return DocumentListResponse(
        items=[_summary(document) for document in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: UUID, session: Session = Depends(get_session)) -> DocumentDetail:
    document = _document_or_404(session, document_id)
    return DocumentDetail(
        **_summary(document).model_dump(),
        size_bytes=document.size_bytes,
        content_hash=document.content_hash,
        error_detail=document.error_detail,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.get("/{document_id}/content")
def document_content(
    document_id: UUID,
    page: int | None = Query(default=None, ge=1),
    session: Session = Depends(get_session),
    settings: Settings = Depends(app_settings),
) -> FileResponse:
    document = _document_or_404(session, document_id)
    corpus_root = settings.resolved_corpus_root
    source_path = (corpus_root / document.source_path).resolve()
    if not source_path.is_relative_to(corpus_root) or not source_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Original source file is unavailable"
        )
    media_type = (
        "application/pdf" if document.extension == ".pdf" else "text/markdown; charset=utf-8"
    )
    # No filename keeps PDFs inline in the browser, allowing the client to apply #page=N.
    response = FileResponse(source_path, media_type=media_type)
    if page is not None:
        response.headers["X-Source-Page"] = str(page)
    return response


def _filters(semester: int | None, course: str | None, document_status: str | None) -> list[object]:
    filters: list[object] = []
    if semester is not None:
        filters.append(Document.semester == semester)
    if course:
        filters.append(Document.course == course)
    if document_status:
        filters.append(Document.status == document_status)
    return filters


def _document_or_404(session: Session, document_id: UUID) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _summary(document: Document) -> DocumentSummary:
    return DocumentSummary(
        id=document.id,
        display_name=document.display_name,
        source_path=document.source_path,
        extension=document.extension,
        semester=document.semester,
        course=document.course,
        page_count=document.page_count,
        extraction_method=document.extraction_method,
        extraction_quality=document.extraction_quality,
        status=document.status,
        error_code=document.error_code,
        indexed_at=document.indexed_at,
    )
