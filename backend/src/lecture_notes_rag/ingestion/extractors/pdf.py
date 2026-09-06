from __future__ import annotations

from pathlib import Path

import fitz

from lecture_notes_rag.ingestion.extractors.models import ExtractedPage, ExtractionResult
from lecture_notes_rag.ingestion.extractors.text import normalize_text, quality_score


def extract_pdf(path: Path) -> ExtractionResult:
    pages: list[ExtractedPage] = []
    with fitz.open(path) as pdf:
        for index, page in enumerate(pdf, start=1):
            text = normalize_text(page.get_text("text", sort=True))
            pages.append(
                ExtractedPage(
                    page_number=index,
                    text=text,
                    heading=_first_nonempty_line(text),
                    extraction_method="native_pdf",
                    extraction_quality=quality_score(text),
                )
            )

    nonempty_pages = [page for page in pages if page.text]
    aggregate_quality = (
        sum(page.extraction_quality for page in pages) / len(pages) if pages else 0.0
    )
    empty_ratio = 1 - (len(nonempty_pages) / len(pages)) if pages else 1.0
    warnings: list[str] = []
    if empty_ratio > 0.25 or aggregate_quality < 0.45:
        warnings.append("low_native_extraction_quality")
    return ExtractionResult(
        pages=pages,
        extraction_method="native_pdf",
        extraction_quality=round(aggregate_quality, 4),
        warnings=warnings,
    )


def _first_nonempty_line(text: str) -> str | None:
    for line in text.splitlines():
        candidate = line.strip()
        if candidate:
            return candidate[:512]
    return None
