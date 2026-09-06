from pathlib import Path

from lecture_notes_rag.ingestion.loaders.discovery import (
    discover_corpus,
    metadata_from_relative_path,
)


def test_discovery_derives_semester_course_hash_and_relative_path(tmp_path: Path) -> None:
    document = tmp_path / "semester_3" / "data_structures" / "queues.pdf"
    document.parent.mkdir(parents=True)
    document.write_bytes(b"not a real PDF")
    (tmp_path / "ignore.txt").write_text("ignored", encoding="utf-8")

    files = discover_corpus(tmp_path)

    assert len(files) == 1
    discovered = files[0]
    assert discovered.relative_path == "semester_3/data_structures/queues.pdf"
    assert discovered.semester == 3
    assert discovered.course == "data_structures"
    assert discovered.content_hash


def test_metadata_does_not_guess_from_an_unstructured_path() -> None:
    assert metadata_from_relative_path(Path("notes.pdf")) == (None, None)
    assert metadata_from_relative_path(Path("misc/notes.pdf")) == (None, None)
