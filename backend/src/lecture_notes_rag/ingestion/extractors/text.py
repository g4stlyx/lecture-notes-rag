from __future__ import annotations

import hashlib
import re
from pathlib import Path

from lecture_notes_rag.ingestion.extractors.models import ExtractedPage, ExtractionResult

_HEADING_PATTERN = re.compile(r"^#{1,6}\s+(?P<heading>.+?)\s*$", re.MULTILINE)
_WHITESPACE_PATTERN = re.compile(r"[ \t]+")
_EXCESS_NEWLINES_PATTERN = re.compile(r"\n{3,}")


def normalize_text(raw_text: str) -> str:
    """Normalize safely while preserving paragraph and code-adjacent newlines."""
    text = raw_text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return _EXCESS_NEWLINES_PATTERN.sub("\n\n", text).strip()


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_markdown(path: Path) -> ExtractionResult:
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    normalized = normalize_text(raw_text)
    heading_match = _HEADING_PATTERN.search(normalized)
    heading = heading_match.group("heading") if heading_match else None
    quality = quality_score(normalized)
    return ExtractionResult(
        pages=[
            ExtractedPage(
                page_number=1,
                text=normalized,
                heading=heading,
                extraction_method="markdown",
                extraction_quality=quality,
            )
        ],
        extraction_method="markdown",
        extraction_quality=quality,
        warnings=[],
    )


def quality_score(text: str) -> float:
    if not text:
        return 0.0
    printable = sum(character.isprintable() or character.isspace() for character in text)
    printable_ratio = printable / len(text)
    suspicious = sum(character == "�" for character in text) / len(text)
    length_score = min(1.0, len(text) / 180)
    return round(max(0.0, (printable_ratio * 0.7) + (length_score * 0.3) - suspicious), 4)
