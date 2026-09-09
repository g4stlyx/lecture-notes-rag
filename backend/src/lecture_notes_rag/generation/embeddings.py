from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from lecture_notes_rag.core.settings import Settings
from lecture_notes_rag.generation.gemini import GeminiProvider

_QWEN_RETRIEVAL_INSTRUCTION = (
    "Given a question about course materials, retrieve relevant lecture-note passages "
    "that answer the question."
)


class EmbeddingProvider(Protocol):
    """Embeds documents and queries in one compatible vector space."""

    @property
    def embedding_model(self) -> str: ...

    @property
    def embedding_dimension(self) -> int: ...

    @property
    def requires_embedding_pacing(self) -> bool: ...

    def embed_documents(self, texts: Sequence[str], titles: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, question: str) -> list[float]: ...


class OllamaEmbeddingError(RuntimeError):
    """Ollama is unavailable or returned an invalid embedding response."""


class GeminiEmbeddingProvider:
    """Embedding-only wrapper around Gemini for optional managed operation."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._provider = GeminiProvider(settings)

    @property
    def embedding_model(self) -> str:
        return self._settings.gemini_embedding_model

    @property
    def embedding_dimension(self) -> int:
        return self._settings.embedding_dimension

    @property
    def requires_embedding_pacing(self) -> bool:
        return True

    def embed_documents(self, texts: Sequence[str], titles: Sequence[str]) -> list[list[float]]:
        return self._provider.embed_documents(texts, titles)

    def embed_query(self, question: str) -> list[float]:
        return self._provider.embed_query(question)


class OllamaEmbeddingProvider:
    """Local embedding adapter backed by Ollama's /api/embed endpoint."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._endpoint = f"{settings.ollama_base_url.rstrip('/')}/api/embed"

    @property
    def embedding_model(self) -> str:
        return f"ollama:{self._settings.ollama_embedding_model}"

    @property
    def embedding_dimension(self) -> int:
        return self._settings.embedding_dimension

    @property
    def requires_embedding_pacing(self) -> bool:
        return False

    def embed_documents(self, texts: Sequence[str], titles: Sequence[str]) -> list[list[float]]:
        if len(texts) != len(titles):
            raise ValueError("texts and titles must have the same length")
        inputs = [f"{title}\n\n{text}" for text, title in zip(texts, titles, strict=True)]
        return self._embed(inputs)

    def embed_query(self, question: str) -> list[float]:
        embeddings = self._embed(
            [f"Instruct: {_QWEN_RETRIEVAL_INSTRUCTION}\nQuery: {question}"]
        )
        if len(embeddings) != 1:
            raise OllamaEmbeddingError("Ollama returned an unexpected number of query embeddings")
        return embeddings[0]

    def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = _post_json(
            self._endpoint,
            {
                "model": self._settings.ollama_embedding_model,
                "input": list(texts),
                "dimensions": self.embedding_dimension,
                "truncate": False,
                "keep_alive": "10m",
            },
            self._settings.ollama_request_timeout_seconds,
        )
        raw_embeddings = response.get("embeddings")
        if not isinstance(raw_embeddings, list) or len(raw_embeddings) != len(texts):
            raise OllamaEmbeddingError("Ollama returned an incomplete embedding batch")

        embeddings: list[list[float]] = []
        for vector in raw_embeddings:
            if not isinstance(vector, list) or len(vector) != self.embedding_dimension:
                raise OllamaEmbeddingError(
                    "Ollama returned embeddings with an unexpected dimension; "
                    f"expected {self.embedding_dimension}."
                )
            try:
                embeddings.append([float(value) for value in vector])
            except (TypeError, ValueError) as error:
                raise OllamaEmbeddingError(
                    "Ollama returned a non-numeric embedding value"
                ) from error
        return embeddings


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "ollama":
        return OllamaEmbeddingProvider(settings)
    return GeminiEmbeddingProvider(settings)


def _post_json(url: str, payload: dict[str, object], timeout_seconds: float) -> dict[str, object]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - configured local URL
            body = response.read().decode("utf-8")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:1_000]
        raise OllamaEmbeddingError(
            f"Ollama embedding request failed ({error.code}): {detail}"
        ) from error
    except URLError as error:
        raise OllamaEmbeddingError(
            "Could not reach Ollama. Start Ollama and confirm OLLAMA_BASE_URL is correct."
        ) from error

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as error:
        raise OllamaEmbeddingError("Ollama returned invalid JSON") from error
    if not isinstance(parsed, dict):
        raise OllamaEmbeddingError("Ollama returned an invalid embedding response")
    return parsed
