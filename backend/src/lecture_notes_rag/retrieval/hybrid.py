from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from lecture_notes_rag.core.settings import Settings
from lecture_notes_rag.domain.schemas import SearchHit, SearchRequest, SourceCitation
from lecture_notes_rag.generation.embeddings import EmbeddingProvider
from lecture_notes_rag.generation.gemini import GroundingContext
from lecture_notes_rag.persistence.models import Chunk, Document

RRF_K = 60


@dataclass(frozen=True)
class RankedChunk:
    chunk: Chunk
    document: Document
    score: float
    vector_rank: int | None
    lexical_rank: int | None


class RetrievalService:
    def __init__(self, session: Session, provider: EmbeddingProvider, settings: Settings):
        self._session = session
        self._provider = provider
        self._settings = settings

    def search(self, request: SearchRequest) -> list[RankedChunk]:
        query_embedding = self._provider.embed_query(request.question)
        candidate_limit = max(request.limit, self._settings.retrieval_candidate_count)
        vector_rows = self._vector_search(query_embedding, request, candidate_limit)
        lexical_rows = self._lexical_search(request, candidate_limit)
        return reciprocal_rank_fusion(vector_rows, lexical_rows, request.limit)

    def _base_query(self, request: SearchRequest) -> Select[tuple[Chunk, Document]]:
        query = select(Chunk, Document).join(Document, Chunk.document_id == Document.id)
        query = query.where(
            Document.status == "ready",
            Chunk.embedding.is_not(None),
            Chunk.embedding_model == self._provider.embedding_model,
            Chunk.embedding_dimension == self._provider.embedding_dimension,
        )
        if request.semester is not None:
            query = query.where(Document.semester == request.semester)
        if request.course:
            query = query.where(Document.course == request.course)
        if request.document_ids:
            query = query.where(Document.id.in_(request.document_ids))
        return query

    def _vector_search(
        self, query_embedding: list[float], request: SearchRequest, limit: int
    ) -> list[tuple[Chunk, Document]]:
        embedding = Chunk.embedding.cast(Vector(self._provider.embedding_dimension))
        distance = embedding.cosine_distance(query_embedding)
        rows = self._session.execute(
            self._base_query(request).order_by(distance).limit(limit)
        ).all()
        return [(chunk, document) for chunk, document in rows]

    def _lexical_search(self, request: SearchRequest, limit: int) -> list[tuple[Chunk, Document]]:
        query_terms = func.plainto_tsquery("simple", request.question)
        rank = func.ts_rank_cd(Chunk.search_vector, query_terms)
        rows = self._session.execute(
            self._base_query(request)
            .where(Chunk.search_vector.op("@@")(query_terms))
            .order_by(rank.desc())
            .limit(limit)
        ).all()
        return [(chunk, document) for chunk, document in rows]


def reciprocal_rank_fusion(
    vector_rows: list[tuple[Chunk, Document]],
    lexical_rows: list[tuple[Chunk, Document]],
    limit: int,
) -> list[RankedChunk]:
    merged: dict[UUID, dict[str, object]] = {}
    for rank, (chunk, document) in enumerate(vector_rows, start=1):
        merged[chunk.id] = {
            "chunk": chunk,
            "document": document,
            "score": 1 / (RRF_K + rank),
            "vector_rank": rank,
            "lexical_rank": None,
        }
    for rank, (chunk, document) in enumerate(lexical_rows, start=1):
        entry = merged.setdefault(
            chunk.id,
            {
                "chunk": chunk,
                "document": document,
                "score": 0.0,
                "vector_rank": None,
                "lexical_rank": None,
            },
        )
        entry["score"] = float(entry["score"]) + (1 / (RRF_K + rank))
        entry["lexical_rank"] = rank

    ranked = [
        RankedChunk(
            chunk=entry["chunk"],  # type: ignore[arg-type]
            document=entry["document"],  # type: ignore[arg-type]
            score=float(entry["score"]),
            vector_rank=entry["vector_rank"],  # type: ignore[arg-type]
            lexical_rank=entry["lexical_rank"],  # type: ignore[arg-type]
        )
        for entry in merged.values()
    ]
    return sorted(ranked, key=lambda item: item.score, reverse=True)[:limit]


def source_citation(result: RankedChunk, label: str) -> SourceCitation:
    return SourceCitation(
        label=label,
        document_id=result.document.id,
        title=result.document.display_name,
        source_path=result.document.source_path,
        semester=result.document.semester,
        course=result.document.course,
        page_start=result.chunk.page_start,
        page_end=result.chunk.page_end,
        excerpt=result.chunk.text[:1_000],
        score=round(result.score, 6),
        open_url=(
            f"/api/v1/documents/{result.document.id}/content?page={result.chunk.page_start}"
        ),
    )


def search_hit(result: RankedChunk, label: str) -> SearchHit:
    return SearchHit(
        **source_citation(result, label).model_dump(),
        vector_rank=result.vector_rank,
        lexical_rank=result.lexical_rank,
    )


def grounding_context(result: RankedChunk, label: str) -> GroundingContext:
    return GroundingContext(
        label=label,
        title=result.document.display_name,
        source_path=result.document.source_path,
        semester=result.document.semester,
        course=result.document.course,
        page_start=result.chunk.page_start,
        page_end=result.chunk.page_end,
        text=result.chunk.text,
    )
