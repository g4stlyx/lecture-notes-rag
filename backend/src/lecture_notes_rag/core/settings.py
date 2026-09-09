from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, PositiveInt, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """Runtime settings loaded only on the server side."""

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_AI_STUDIO_API_KEY"),
        repr=False,
    )
    gemini_generation_model: str = "gemini-3.7-flash"
    gemini_embedding_model: str = "gemini-embedding-2"
    embedding_provider: Literal["gemini", "ollama"] = "ollama"
    embedding_dimension: PositiveInt = 1024
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    ollama_request_timeout_seconds: PositiveInt = 120

    database_url: str = (
        "postgresql+psycopg://lecture_notes:lecture_notes_dev@localhost:5432/lecture_notes"
    )
    corpus_root: Path = Path("data")
    runtime_root: Path = Path("runtime")

    chunk_size_tokens: PositiveInt = 700
    chunk_overlap_tokens: PositiveInt = 90
    retrieval_candidate_count: PositiveInt = 12
    retrieval_context_count: PositiveInt = 6
    max_context_characters: PositiveInt = 30_000
    # Gemini free-tier accounts commonly have a 100 RPM embedding quota. Larger
    # request batches and a conservative pacer prevent the worker from burning
    # through it in seconds.
    # Gemini's BatchEmbedContents endpoint accepts many inputs at once, but free
    # tier quota is charged per embedded content. Ten is a practical transport
    # batch that stays within the per-minute request budget when paced by item.
    embedding_batch_size: PositiveInt = 10
    embedding_requests_per_minute: PositiveInt = 80
    embedding_max_retries: PositiveInt = 8
    embedding_max_retry_delay_seconds: PositiveInt = 120

    @model_validator(mode="after")
    def validate_vector_dimension(self) -> Settings:
        if self.embedding_provider == "gemini" and self.embedding_dimension != 1536:
            raise ValueError(
                "GEMINI_EMBEDDING_MODEL requires EMBEDDING_DIMENSION=1536."
            )
        if (
            self.embedding_provider == "ollama"
            and self.ollama_embedding_model == "qwen3-embedding:0.6b"
            and self.embedding_dimension != 1024
        ):
            raise ValueError("qwen3-embedding:0.6b requires EMBEDDING_DIMENSION=1024.")
        return self

    @property
    def resolved_corpus_root(self) -> Path:
        return self._resolve_repository_path(self.corpus_root)

    @property
    def resolved_runtime_root(self) -> Path:
        return self._resolve_repository_path(self.runtime_root)

    @staticmethod
    def _resolve_repository_path(path: Path) -> Path:
        return path if path.is_absolute() else (REPOSITORY_ROOT / path).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
