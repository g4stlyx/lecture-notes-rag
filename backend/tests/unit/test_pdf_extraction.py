from pathlib import Path

import fitz

from lecture_notes_rag.ingestion.extractors.pdf import extract_pdf


def test_pdf_extraction_keeps_one_based_page_numbers(tmp_path: Path) -> None:
    path = tmp_path / "lecture.pdf"
    with fitz.open() as document:
        first = document.new_page()
        first.insert_text((72, 72), "First page: algorithms")
        second = document.new_page()
        second.insert_text((72, 72), "Second page: queues")
        document.save(path)

    extraction = extract_pdf(path)

    assert [page.page_number for page in extraction.pages] == [1, 2]
    assert "algorithms" in extraction.pages[0].text
    assert "queues" in extraction.pages[1].text
