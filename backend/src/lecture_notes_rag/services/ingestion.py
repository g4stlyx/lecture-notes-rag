from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from lecture_notes_rag.core.settings import Settings
from lecture_notes_rag.generation.gemini import GeminiProvider
from lecture_notes_rag.ingestion.chunking.page_chunker import chunk_pages
from lecture_notes_rag.ingestion.extractors.models import ExtractionResult
from lecture_notes_rag.ingestion.extractors.ocr import OcrUnavailableError, extract_pdf_with_ocr
from lecture_notes_rag.ingestion.extractors.pdf import extract_pdf
from lecture_notes_rag.ingestion.extractors.text import extract_markdown, text_hash
from lecture_notes_rag.ingestion.loaders.discovery import DiscoveredFile, discover_corpus
from lecture_notes_rag.persistence.models import Chunk, Document, IngestionJob, Page

logger = logging.getLogger(__name__)
PIPELINE_VERSION = "1"


class IngestionService:
    def __init__(self, session: Session, provider: GeminiProvider, settings: Settings):
        self._session = session
        self._provider = provider
        self._settings = settings

    def run(self, job_id: UUID) -> None:
        job = self._session.get(IngestionJob, job_id)
        if job is None:
            raise LookupError(f"Ingestion job {job_id} does not exist")

        job.status = "running"
        job.started_at = datetime.now(UTC)
        self._session.commit()

        try:
            files = discover_corpus(self._settings.resolved_corpus_root)
            job.discovered_count = len(files)
            self._session.commit()
            self._mark_missing_documents_stale({file.relative_path for file in files})

            for file in files:
                try:
                    if self._is_current(file, job.force):
                        job.skipped_count += 1
                    else:
                        self._ingest_file(file)
                        job.processed_count += 1
                except (
                    Exception
                ) as error:  # Continue so one corrupt PDF does not kill the corpus job.
                    logger.exception("Ingestion failed for %s", file.relative_path)
                    self._record_file_failure(file, error)
                    job.failed_count += 1
                finally:
                    self._session.commit()

            job.status = "completed"
        except Exception as error:
            logger.exception("Ingestion job %s failed", job_id)
            job.status = "failed"
            job.error_summary = str(error)[:2_000]
        finally:
            job.completed_at = datetime.now(UTC)
            self._session.commit()

    def _is_current(self, file: DiscoveredFile, force: bool) -> bool:
        if force:
            return False
        existing = self._session.scalar(
            select(Document).where(Document.source_path == file.relative_path)
        )
        return bool(
            existing
            and existing.status == "ready"
            and existing.content_hash == file.content_hash
            and existing.pipeline_version == PIPELINE_VERSION
        )

    def _ingest_file(self, file: DiscoveredFile) -> None:
        document = self._get_or_create_document(file)
        document.status = "processing"
        document.error_code = None
        document.error_detail = None
        self._session.flush()

        extraction = self._extract(file)
        chunks = chunk_pages(
            extraction.pages,
            self._settings.chunk_size_tokens,
            self._settings.chunk_overlap_tokens,
        )
        if not chunks:
            raise ValueError("No indexable text was extracted from document")

        self._session.execute(delete(Chunk).where(Chunk.document_id == document.id))
        self._session.execute(delete(Page).where(Page.document_id == document.id))
        self._session.flush()

        document.page_count = len(extraction.pages)
        document.extraction_method = extraction.extraction_method
        document.extraction_quality = extraction.extraction_quality
        document.pipeline_version = PIPELINE_VERSION
        for page in extraction.pages:
            document.pages.append(
                Page(
                    page_number=page.page_number,
                    text=page.text,
                    heading=page.heading,
                    extraction_method=page.extraction_method,
                    extraction_quality=page.extraction_quality,
                    content_hash=text_hash(page.text),
                )
            )

        persisted_chunks = [
            Chunk(
                page_start=candidate.page_start,
                page_end=candidate.page_end,
                section_heading=candidate.section_heading,
                chunk_index=candidate.chunk_index,
                text=candidate.text,
                token_count=candidate.token_count,
                content_hash=candidate.content_hash,
                parser_version=PIPELINE_VERSION,
                chunker_version=PIPELINE_VERSION,
            )
            for candidate in chunks
        ]
        document.chunks.extend(persisted_chunks)
        self._session.flush()
        self._embed_chunks(document, persisted_chunks)

        document.status = "ready"
        document.indexed_at = datetime.now(UTC)
        if extraction.warnings:
            document.error_detail = "; ".join(extraction.warnings)

    def _get_or_create_document(self, file: DiscoveredFile) -> Document:
        document = self._session.scalar(
            select(Document).where(Document.source_path == file.relative_path)
        )
        modified_at = datetime.fromtimestamp(file.path.stat().st_mtime, tz=UTC)
        if document is None:
            document = Document(
                source_path=file.relative_path,
                display_name=file.path.name,
                extension=file.extension,
                mime_type=_mime_type(file.extension),
                semester=file.semester,
                course=file.course,
                content_hash=file.content_hash,
                size_bytes=file.size_bytes,
                modified_at=modified_at,
            )
            self._session.add(document)
        else:
            document.display_name = file.path.name
            document.extension = file.extension
            document.mime_type = _mime_type(file.extension)
            document.semester = file.semester
            document.course = file.course
            document.content_hash = file.content_hash
            document.size_bytes = file.size_bytes
            document.modified_at = modified_at
        return document

    def _extract(self, file: DiscoveredFile) -> ExtractionResult:
        if file.extension == ".md":
            return extract_markdown(file.path)
        result = extract_pdf(file.path)
        if "low_native_extraction_quality" not in result.warnings:
            return result

        artifact_path = self._settings.resolved_runtime_root / "ocr" / f"{file.content_hash}.pdf"
        try:
            return extract_pdf_with_ocr(file.path, artifact_path)
        except OcrUnavailableError:
            logger.warning(
                "OCR unavailable; retaining native extraction for %s", file.relative_path
            )
            return result

    def _embed_chunks(self, document: Document, chunks: list[Chunk]) -> None:
        for offset in range(0, len(chunks), self._settings.embedding_batch_size):
            batch = chunks[offset : offset + self._settings.embedding_batch_size]
            vectors = self._provider.embed_documents(
                [chunk.text for chunk in batch],
                [document.display_name] * len(batch),
            )
            if len(vectors) != len(batch):
                raise RuntimeError("Gemini returned an incomplete embedding batch")
            for chunk, vector in zip(batch, vectors, strict=True):
                chunk.embedding = vector
                chunk.embedding_model = self._settings.gemini_embedding_model
                chunk.embedding_dimension = len(vector)

    def _record_file_failure(self, file: DiscoveredFile, error: Exception) -> None:
        document = self._get_or_create_document(file)
        document.status = "failed"
        document.error_code = type(error).__name__[:128]
        document.error_detail = str(error)[:2_000]

    def _mark_missing_documents_stale(self, discovered_paths: set[str]) -> None:
        if not discovered_paths:
            return
        self._session.execute(
            update(Document)
            .where(Document.source_path.not_in(discovered_paths), Document.status != "stale")
            .values(status="stale")
        )
        self._session.commit()


def _mime_type(extension: str) -> str:
    return {".pdf": "application/pdf", ".md": "text/markdown"}[extension]
