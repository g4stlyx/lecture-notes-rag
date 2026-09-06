from __future__ import annotations

from dataclasses import dataclass

from lecture_notes_rag.ingestion.extractors.models import ExtractedPage
from lecture_notes_rag.ingestion.extractors.text import text_hash


@dataclass(frozen=True)
class ChunkCandidate:
    page_start: int
    page_end: int
    section_heading: str | None
    chunk_index: int
    text: str
    token_count: int
    content_hash: str


def chunk_pages(
    pages: list[ExtractedPage], chunk_size_tokens: int, overlap_tokens: int
) -> list[ChunkCandidate]:
    """Chunk each page independently so a citation always has an unambiguous page."""
    if overlap_tokens >= chunk_size_tokens:
        raise ValueError("overlap_tokens must be smaller than chunk_size_tokens")

    candidates: list[ChunkCandidate] = []
    for page in pages:
        words = page.text.split()
        if not words:
            continue
        start = 0
        while start < len(words):
            end = min(len(words), start + chunk_size_tokens)
            text = " ".join(words[start:end]).strip()
            candidates.append(
                ChunkCandidate(
                    page_start=page.page_number,
                    page_end=page.page_number,
                    section_heading=page.heading,
                    chunk_index=len(candidates),
                    text=text,
                    token_count=len(words[start:end]),
                    content_hash=text_hash(text),
                )
            )
            if end == len(words):
                break
            start = end - overlap_tokens
    return candidates
