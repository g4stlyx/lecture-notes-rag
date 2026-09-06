from lecture_notes_rag.ingestion.chunking.page_chunker import chunk_pages
from lecture_notes_rag.ingestion.extractors.models import ExtractedPage


def test_page_chunks_preserve_page_provenance_and_overlap() -> None:
    page = ExtractedPage(
        page_number=7,
        text=" ".join(f"word-{index}" for index in range(10)),
        heading="Stacks",
        extraction_method="native_pdf",
        extraction_quality=1.0,
    )

    chunks = chunk_pages([page], chunk_size_tokens=5, overlap_tokens=2)

    assert [chunk.token_count for chunk in chunks] == [5, 5, 4]
    assert all(chunk.page_start == 7 and chunk.page_end == 7 for chunk in chunks)
    assert chunks[0].section_heading == "Stacks"
    assert chunks[0].text.endswith("word-4")
    assert chunks[1].text.startswith("word-3")


def test_chunker_rejects_an_overlap_as_large_as_the_chunk() -> None:
    page = ExtractedPage(1, "one two", None, "markdown", 1.0)

    try:
        chunk_pages([page], chunk_size_tokens=2, overlap_tokens=2)
    except ValueError as error:
        assert "smaller" in str(error)
    else:
        raise AssertionError("Expected invalid chunk overlap to fail")
