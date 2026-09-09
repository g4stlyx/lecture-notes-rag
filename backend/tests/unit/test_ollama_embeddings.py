import pytest

from lecture_notes_rag.core.settings import Settings
from lecture_notes_rag.generation.embeddings import (
    OllamaEmbeddingError,
    OllamaEmbeddingProvider,
    get_embedding_provider,
)


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "embedding_provider": "ollama",
        "embedding_dimension": 1024,
        "ollama_base_url": "http://127.0.0.1:11434",
        "ollama_embedding_model": "qwen3-embedding:0.6b",
    }
    values.update(overrides)
    return Settings(**values)


def test_ollama_embeddings_batch_documents_and_formats_queries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[dict[str, object]] = []

    def fake_post(
        url: str, payload: dict[str, object], timeout_seconds: float
    ) -> dict[str, object]:
        assert url == "http://127.0.0.1:11434/api/embed"
        assert timeout_seconds == 120
        requests.append(payload)
        inputs = payload["input"]
        assert isinstance(inputs, list)
        return {"embeddings": [[float(index)] * 1024 for index, _ in enumerate(inputs, 1)]}

    monkeypatch.setattr("lecture_notes_rag.generation.embeddings._post_json", fake_post)
    provider = OllamaEmbeddingProvider(_settings())

    documents = provider.embed_documents(["Matrix multiplication"], ["Linear Algebra"])
    query = provider.embed_query("How do I multiply matrices?")

    assert documents == [[1.0] * 1024]
    assert query == [1.0] * 1024
    assert requests[0]["input"] == ["Linear Algebra\n\nMatrix multiplication"]
    assert requests[0]["dimensions"] == 1024
    assert requests[1]["input"] == [
        "Instruct: Given a question about course materials, retrieve relevant lecture-note "
        "passages that answer the question.\nQuery: How do I multiply matrices?"
    ]


def test_ollama_provider_rejects_wrong_vector_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lecture_notes_rag.generation.embeddings._post_json",
        lambda *_: {"embeddings": [[0.0] * 10]},
    )

    with pytest.raises(OllamaEmbeddingError, match="unexpected dimension"):
        OllamaEmbeddingProvider(_settings()).embed_query("What is a vector?")


def test_qwen_06b_requires_its_native_embedding_dimension() -> None:
    with pytest.raises(ValueError, match="requires EMBEDDING_DIMENSION=1024"):
        _settings(embedding_dimension=768)


def test_ollama_is_the_default_embedding_provider() -> None:
    assert isinstance(get_embedding_provider(_settings()), OllamaEmbeddingProvider)
