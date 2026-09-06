from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HealthResponse(ApiModel):
    status: str
    database_ready: bool
    gemini_configured: bool


class DocumentSummary(ApiModel):
    id: UUID
    display_name: str
    source_path: str
    extension: str
    semester: int | None
    course: str | None
    page_count: int | None
    extraction_method: str | None
    extraction_quality: float | None
    status: str
    error_code: str | None
    indexed_at: datetime | None


class DocumentDetail(DocumentSummary):
    size_bytes: int
    content_hash: str
    error_detail: str | None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(ApiModel):
    items: list[DocumentSummary]
    total: int
    page: int
    page_size: int


class IngestionJobRequest(ApiModel):
    force: bool = False


class IngestionJobResponse(ApiModel):
    id: UUID
    status: str
    discovered_count: int
    processed_count: int
    skipped_count: int
    failed_count: int
    started_at: datetime | None
    completed_at: datetime | None
    error_summary: str | None


class SearchRequest(ApiModel):
    question: str = Field(min_length=2, max_length=4_000)
    semester: int | None = Field(default=None, ge=1, le=8)
    course: str | None = Field(default=None, max_length=160)
    document_ids: list[UUID] | None = Field(default=None, max_length=30)
    limit: int = Field(default=6, ge=1, le=20)


class SourceCitation(ApiModel):
    label: str
    document_id: UUID
    title: str
    source_path: str
    semester: int | None
    course: str | None
    page_start: int
    page_end: int
    excerpt: str
    score: float
    open_url: str


class SearchHit(SourceCitation):
    vector_rank: int | None = None
    lexical_rank: int | None = None


class SearchResponse(ApiModel):
    hits: list[SearchHit]
    query: str


class ChatRequest(SearchRequest):
    conversation_id: UUID | None = None


class ChatResponse(ApiModel):
    conversation_id: UUID
    answer: str
    sources: list[SourceCitation]
    grounded: bool
    model: str | None
    latency_ms: int


class GeminiAnswerDraft(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)
    grounded: bool = False


class StreamEvent(ApiModel):
    type: str
    data: dict[str, Any]
