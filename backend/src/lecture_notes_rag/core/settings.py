from __future__ import annotations

from functools import lru_cache
from pathlib import Path

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
    embedding_dimension: PositiveInt = 1536

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
    embedding_batch_size: PositiveInt = 32

    @model_validator(mode="after")
    def validate_vector_dimension(self) -> Settings:
        if self.embedding_dimension != 1536:
            raise ValueError(
                "EMBEDDING_DIMENSION must be 1536 until a matching pgvector migration is applied."
            )
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
