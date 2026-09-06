from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    heading: str | None
    extraction_method: str
    extraction_quality: float


@dataclass(frozen=True)
class ExtractionResult:
    pages: list[ExtractedPage]
    extraction_method: str
    extraction_quality: float
    warnings: list[str]
