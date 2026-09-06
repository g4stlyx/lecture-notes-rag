from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from lecture_notes_rag.ingestion.extractors.models import ExtractionResult
from lecture_notes_rag.ingestion.extractors.pdf import extract_pdf


class OcrUnavailableError(RuntimeError):
    pass


def extract_pdf_with_ocr(source_path: Path, output_path: Path) -> ExtractionResult:
    """Create a searchable derivative and re-extract it, preserving page numbering."""
    executable = shutil.which("ocrmypdf")
    if executable is None:
        raise OcrUnavailableError("OCRmyPDF is not installed or not on PATH")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [executable, "--skip-text", "--output-type", "pdf", str(source_path), str(output_path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=1_200,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()[-500:]
        raise RuntimeError(f"OCRmyPDF failed with exit code {completed.returncode}: {stderr}")
    result = extract_pdf(output_path)
    return ExtractionResult(
        pages=[
            page.__class__(
                page_number=page.page_number,
                text=page.text,
                heading=page.heading,
                extraction_method="ocr_pdf",
                extraction_quality=page.extraction_quality,
            )
            for page in result.pages
        ],
        extraction_method="ocr_pdf",
        extraction_quality=result.extraction_quality,
        warnings=result.warnings,
    )
