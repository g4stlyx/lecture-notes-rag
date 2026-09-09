from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from lecture_notes_rag.api.dependencies import (
    app_settings,
    require_embedding_provider,
    require_gemini_provider,
)
from lecture_notes_rag.core.settings import Settings
from lecture_notes_rag.domain.schemas import (
    ChatRequest,
    ChatResponse,
    SearchRequest,
    SearchResponse,
)
from lecture_notes_rag.generation.embeddings import EmbeddingProvider
from lecture_notes_rag.generation.gemini import GeminiGenerationUnavailableError, GeminiProvider
from lecture_notes_rag.persistence.database import get_session
from lecture_notes_rag.retrieval.hybrid import RetrievalService, search_hit
from lecture_notes_rag.services.chat import ChatService

router = APIRouter(tags=["chat"])


@router.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    session: Session = Depends(get_session),
    provider: EmbeddingProvider = Depends(require_embedding_provider),
    settings: Settings = Depends(app_settings),
) -> SearchResponse:
    results = RetrievalService(session, provider, settings).search(payload)
    return SearchResponse(
        query=payload.question,
        hits=[search_hit(result, f"S{index}") for index, result in enumerate(results, 1)],
    )


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    session: Session = Depends(get_session),
    embedding_provider: EmbeddingProvider = Depends(require_embedding_provider),
    answer_provider: GeminiProvider = Depends(require_gemini_provider),
    settings: Settings = Depends(app_settings),
) -> ChatResponse:
    try:
        return ChatService(session, embedding_provider, answer_provider, settings).answer(payload)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except GeminiGenerationUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/chat/stream")
def stream_chat(
    payload: ChatRequest,
    session: Session = Depends(get_session),
    embedding_provider: EmbeddingProvider = Depends(require_embedding_provider),
    answer_provider: GeminiProvider = Depends(require_gemini_provider),
    settings: Settings = Depends(app_settings),
) -> StreamingResponse:
    """SSE compatibility endpoint. Citation validation completes before sources are emitted."""
    try:
        response = ChatService(
            session, embedding_provider, answer_provider, settings
        ).answer(payload)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except GeminiGenerationUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    def events() -> Iterator[str]:
        for word in response.answer.split(" "):
            yield _event("token", {"text": f"{word} "})
        yield _event(
            "sources", {"sources": [source.model_dump(mode="json") for source in response.sources]}
        )
        yield _event(
            "done",
            {
                "conversationId": str(response.conversation_id),
                "grounded": response.grounded,
                "latencyMs": response.latency_ms,
            },
        )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _event(event_type: str, payload: dict[str, object]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
