from __future__ import annotations

import time
from uuid import UUID

from sqlalchemy.orm import Session

from lecture_notes_rag.core.settings import Settings
from lecture_notes_rag.domain.schemas import ChatRequest, ChatResponse
from lecture_notes_rag.generation.embeddings import EmbeddingProvider
from lecture_notes_rag.generation.gemini import GeminiProvider, validate_answer_draft
from lecture_notes_rag.persistence.models import Conversation, Message
from lecture_notes_rag.retrieval.hybrid import RetrievalService, grounding_context, source_citation


class ChatService:
    def __init__(
        self,
        session: Session,
        embedding_provider: EmbeddingProvider,
        answer_provider: GeminiProvider,
        settings: Settings,
    ):
        self._session = session
        self._embedding_provider = embedding_provider
        self._answer_provider = answer_provider
        self._settings = settings

    def answer(self, request: ChatRequest) -> ChatResponse:
        started = time.perf_counter()
        conversation = self._resolve_conversation(request.conversation_id, request.question)
        filters = {
            "semester": request.semester,
            "course": request.course,
            "document_ids": [str(identifier) for identifier in request.document_ids or []],
        }
        self._session.add(
            Message(
                conversation_id=conversation.id, role="user", text=request.question, filters=filters
            )
        )

        retrieval = RetrievalService(self._session, self._embedding_provider, self._settings)
        results = retrieval.search(request)
        result_context = results[: self._settings.retrieval_context_count]
        sources = [
            source_citation(result, f"S{index}") for index, result in enumerate(result_context, 1)
        ]

        if not result_context:
            answer = "I could not find supporting material in the indexed lecture notes."
            grounded = False
            model = None
        else:
            draft = self._answer_provider.answer(
                request.question,
                [
                    grounding_context(result, source.label)
                    for result, source in zip(result_context, sources, strict=True)
                ],
            )
            validated = validate_answer_draft(draft, {source.label for source in sources})
            answer = validated.answer
            grounded = validated.grounded
            sources = [source for source in sources if source.label in validated.citations]
            model = self._settings.gemini_generation_model

        latency_ms = round((time.perf_counter() - started) * 1_000)
        self._session.add(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                text=answer,
                filters=filters,
                retrieved_chunk_ids=[str(result.chunk.id) for result in result_context],
                sources=[source.model_dump(mode="json") for source in sources],
                model=model,
                latency_ms=latency_ms,
            )
        )
        self._session.commit()
        return ChatResponse(
            conversation_id=conversation.id,
            answer=answer,
            sources=sources,
            grounded=grounded,
            model=model,
            latency_ms=latency_ms,
        )

    def _resolve_conversation(self, conversation_id: UUID | None, question: str) -> Conversation:
        if conversation_id is not None:
            conversation = self._session.get(Conversation, conversation_id)
            if conversation is None:
                raise LookupError("Conversation does not exist")
            return conversation
        conversation = Conversation(title=question[:120])
        self._session.add(conversation)
        self._session.flush()
        return conversation
