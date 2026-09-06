# Lecture Notes RAG — Implementation Plan

Status: architecture and execution plan only  
Last updated: 2026-09-06  
Corpus snapshot: 225 files (222 PDF, 3 Markdown), approximately 354.53 MB

## 1. Goal

Build a private web application that answers questions from eight semesters of
lecture material and makes every factual answer auditable. A user must be able
to see which document, semester, course, and page supports each claim and open
the original source at that page.

The first release is a single-user, locally deployable system. Its boundaries
must still support later multi-user deployment, background workers, larger
corpora, and replacement of Gemini or the vector store without rewriting the
domain layer.

## 2. Product scope

### MVP capabilities

- Discover and index the existing `data/semester_*/<course>/` corpus.
- Parse text-native PDFs and Markdown while preserving page/section provenance.
- Detect weak or empty PDF extraction and use OCR as a fallback.
- Incrementally re-index only new or changed files.
- Ask questions across all notes or filter by semester, course, and document.
- Stream Gemini-generated answers to the browser.
- Show inline citation markers such as `[S1]`, with a source panel containing:
  document title, relative path, semester, course, page range, matching excerpt,
  and retrieval score.
- Open the original PDF at the cited page.
- Refuse or qualify answers when retrieved evidence is insufficient.
- Expose ingestion state, failed documents, and indexing statistics.

### Explicitly deferred

- User accounts, permissions, cloud object storage, and public internet access.
- Collaborative annotations or note editing.
- Audio/video ingestion.
- Automatic web search or facts outside the uploaded corpus.
- Knowledge graphs and agentic multi-step research.
- Fine-tuning a model.

## 3. Architecture decision

Use a modular monolith with a React/TypeScript client, Python/FastAPI backend,
PostgreSQL plus pgvector, and Gemini behind provider adapters.

```text
Browser
   |  REST + Server-Sent Events
   v
FastAPI application
   |-- corpus/catalog service
   |-- ingestion pipeline ----> parser/OCR ----> chunker ----> Gemini embeddings
   |-- query pipeline --------> filters + hybrid retrieval + optional reranking
   |-- answer service --------> Gemini generation + citation validation
   |
   +--> PostgreSQL: documents, pages, chunks, vectors, FTS, jobs, conversations
   +--> Local filesystem: original source files and derived extraction artifacts
```

Why not use Gemini File Search as the primary store: it reduces infrastructure
and now supports page-aware grounding, but it places ingestion, ranking behavior,
debugging, and lifecycle control behind a managed service. The custom baseline
is more work, but citation integrity, metadata filtering, observability, and
provider portability are core requirements here. File Search remains a valid
future adapter or a fast comparison baseline.

## 4. Technology choices

| Concern | Planned choice | Reason |
|---|---|---|
| Backend | Python 3.12+, FastAPI, Pydantic | Strong document/ML ecosystem and typed HTTP contracts |
| Frontend | React, TypeScript, Vite | Fast local UI and clean streaming/citation UX |
| Gemini SDK | `google-genai` | Current official Google Gen AI SDK |
| Generation | Stable Gemini Flash model, selected by environment | Good latency/cost baseline; model can change without code changes |
| Embeddings | `gemini-embedding-2`, initially 1,536 dimensions | Current stable multilingual/multimodal embedding model; balanced storage/quality |
| PDF parsing | PyMuPDF first; extraction-quality gate | Fast, page-native extraction for born-digital PDFs |
| OCR fallback | OCRmyPDF/Tesseract adapter | Local and deterministic fallback for scanned pages |
| Database | PostgreSQL + pgvector | Vectors, metadata, full-text search, transactions, and filtering in one system |
| Retrieval | Hybrid vector + PostgreSQL FTS, fused with RRF | Better coverage for concepts, acronyms, equations, and exact terminology |
| Streaming | Server-Sent Events | Simpler than WebSockets for one-way answer streams |
| Local runtime | Docker Compose | Reproducible database and service startup |
| Tests | pytest; frontend unit/component tests; Playwright later | Covers core logic, contracts, and critical user flow |

Do not couple the core pipeline to LangChain or LlamaIndex. Small provider and
repository interfaces keep behavior explicit and testable; either framework can
be adopted later for a feature that clearly earns the dependency.

## 5. Repository layout

```text
lecture-notes-rag/
|-- .env                    # existing local secret; never commit
|-- .env.example            # variable names only
|-- .gitignore
|-- data/                   # canonical source corpus; treat as read-only
|   |-- semester_1/
|   `-- ... semester_8/
|-- backend/
|   |-- src/lecture_notes_rag/
|   |   |-- api/routes/     # HTTP/SSE endpoints only
|   |   |-- core/           # configuration, logging, errors, telemetry
|   |   |-- domain/         # models and provider/repository protocols
|   |   |-- ingestion/
|   |   |   |-- loaders/    # discovery, hashes, PDF and Markdown loading
|   |   |   |-- extractors/ # native PDF extraction and OCR adapters
|   |   |   `-- chunking/   # page/section-aware chunk policies
|   |   |-- retrieval/      # query planning, hybrid search, fusion, reranking
|   |   |-- generation/     # Gemini adapter, prompts, citation validation
|   |   |-- persistence/    # PostgreSQL repositories and mappings
|   |   |-- services/       # application use cases
|   |   `-- workers/        # ingestion/indexing job handlers
|   |-- migrations/
|   `-- tests/
|       |-- unit/
|       |-- integration/
|       `-- evaluation/
|-- frontend/
|   |-- public/
|   `-- src/
|       |-- app/
|       |-- components/
|       |-- features/
|       |   |-- chat/
|       |   |-- library/
|       |   `-- sources/
|       |-- hooks/
|       |-- lib/
|       `-- types/
|-- evals/
|   |-- datasets/           # human-authored questions and expected sources
|   `-- reports/            # generated metrics; ignored except placeholders
|-- docs/
|   -- IMPLEMENTATION_PLAN.md
|   `-- adr/                # architecture decision records
|-- infra/
|   `-- docker/
|-- scripts/                # operator entry points, not domain logic
`-- runtime/                # generated, disposable local artifacts
    |-- extracted/
    |-- ocr/
    |-- cache/
    `-- logs/
```

The existing `data/` paths encode useful metadata. Ingestion derives `semester`
and `course` from the relative path but persists normalized metadata, so files
can be reorganized later without changing API contracts.

## 6. Core data model

### `documents`

- `id` (UUID)
- `source_path` (unique normalized relative path)
- `display_name`, `extension`, `mime_type`
- `semester`, `course`
- `content_hash`, `size_bytes`, `modified_at`
- `page_count`, `language`
- `extraction_method`, `extraction_quality`
- `status` (`discovered`, `processing`, `ready`, `failed`, `stale`)
- `error_code`, `error_detail`
- timestamps and ingestion version

### `pages`

- `id`, `document_id`, `page_number`
- normalized text and optional heading
- extraction method and quality metrics
- derived artifact reference, if an OCR/page preview exists
- content hash

### `chunks`

- `id`, `document_id`
- `page_start`, `page_end`, optional section heading
- `chunk_index`, text, token count
- `content_hash`, parser version, chunker version
- embedding vector and embedding model/version/dimension
- PostgreSQL full-text-search column

### `ingestion_jobs`

- job ID, type, state, progress counts, timestamps, retry count, error summary

### `conversations` and `messages`

- conversation/message IDs, role, text, timestamps
- selected filters and generation settings
- retrieved chunk IDs, scores, prompt/model version, latency, token usage

Store the retrieval trace with each answer. This makes regressions debuggable
and lets evaluation replay the exact evidence set.

## 7. Ingestion pipeline

1. Discover `.pdf` and `.md` files below `data/`; ignore generated/system files.
2. Validate path, extension, MIME signature, size, and readability.
3. Compute a streaming SHA-256 hash. Skip a document when its hash and pipeline
   version have already been indexed.
4. Derive semester/course metadata from the path and create/update the catalog.
5. Extract per page:
   - PDF: use native extraction first.
   - Markdown: preserve headings, code fences, lists, and source line ranges.
6. Score PDF extraction quality using characters per page, printable-character
   ratio, empty-page ratio, and suspicious glyph frequency.
7. OCR only the failing pages/document. Preserve original PDF page numbering.
8. Normalize repeated headers/footers, whitespace, and hyphenation conservatively.
   Never discard original extracted text until the normalized result is verified.
9. Chunk around page and heading boundaries. Initial experiment range:
   500–900 tokens with 10–15% overlap. Avoid splitting code blocks, definitions,
   equations, and tables where detectable.
10. Attach complete provenance metadata to every chunk.
11. Batch embeddings with bounded concurrency, exponential backoff, and resumable
    checkpoints. Use asymmetric retrieval instructions consistently for document
    and query embeddings.
12. Upsert the new document version transactionally; remove superseded chunks
    only after the replacement is complete.
13. Emit a manifest with successes, skips, OCR use, failures, duration, and cost.

Deletion policy: a missing source becomes `stale` first. Physical deletion from
the index is an explicit operator action, protecting against accidental corpus
loss or a temporarily unavailable mount.

## 8. Retrieval and answer pipeline

1. Validate the question and user-selected semester/course/document filters.
2. Optionally rewrite follow-up questions into standalone queries using bounded
   conversation context; retain the original wording for display/audit.
3. Generate the query embedding.
4. Run filtered vector search and filtered full-text search in parallel.
5. Fuse results with Reciprocal Rank Fusion and deduplicate near-identical chunks.
6. Expand adjacent chunks when a result cuts across a page/section boundary.
7. Optionally rerank the top candidates only if evaluation shows material gains.
8. Apply a configurable evidence threshold. If it fails, return a clear
   insufficient-evidence response rather than asking Gemini to improvise.
9. Build a token-budgeted context containing immutable source labels (`S1`, `S2`,
   ...), document metadata, page ranges, and excerpts.
10. Ask Gemini for a structured answer whose citations may reference only those
    labels. The instruction treats retrieved document text as untrusted data, not
    system commands.
11. Server-side validation rejects unknown labels, maps valid labels to source
    records, and records unsupported/uncited claims for observability.
12. Stream answer text and finish with a canonical source payload and metrics.

Do not trust model-created filenames, URLs, or page numbers. The server owns the
source registry and builds citation links from stored metadata.

## 9. Citation contract and UI

Example response shape (contract design, not implementation):

```json
{
  "answer": "A stack follows LIFO ordering [S1].",
  "sources": [
    {
      "label": "S1",
      "documentId": "uuid",
      "title": "6StacksQueues.pdf",
      "semester": 3,
      "course": "data_structures",
      "pageStart": 4,
      "pageEnd": 5,
      "excerpt": "...",
      "score": 0.84,
      "openUrl": "/api/v1/documents/uuid/content?page=4"
    }
  ],
  "grounded": true
}
```

The chat view renders citation chips inline. Selecting one opens a source drawer
with the excerpt and retrieval metadata; an explicit action opens the PDF viewer
at the correct 1-based page. The library view lists every document, its indexing
state, extraction type, page count, and last indexed time.

## 10. Initial API surface

- `GET /api/v1/health` — liveness and dependency readiness.
- `GET /api/v1/documents` — paginated/filterable corpus catalog.
- `GET /api/v1/documents/{id}` — metadata and extraction status.
- `GET /api/v1/documents/{id}/content` — safe PDF/Markdown delivery with page hint.
- `POST /api/v1/ingestion/jobs` — start discovery/indexing.
- `GET /api/v1/ingestion/jobs/{id}` — progress and failures.
- `POST /api/v1/search` — retrieval-only diagnostics.
- `POST /api/v1/chat` — non-streaming fallback.
- `POST /api/v1/chat/stream` — SSE answer stream.
- `GET/POST /api/v1/conversations` — conversation listing/creation.
- `GET /api/v1/conversations/{id}/messages` — replay with citations.

The retrieval-only endpoint is important: it separates “could not retrieve the
right evidence” from “Gemini answered poorly with good evidence.” Keep detailed
scores behind a debug flag in production.

## 11. Configuration and secrets

Planned environment variables:

- `GEMINI_API_KEY`
- `GEMINI_GENERATION_MODEL`
- `GEMINI_EMBEDDING_MODEL`
- `EMBEDDING_DIMENSION`
- `DATABASE_URL`
- `CORPUS_ROOT`
- `RUNTIME_ROOT`
- retrieval/chunking/token-budget settings
- log level and environment name

The current `.env` uses `GOOGLE_AI_STUDIO_API_KEY`. During implementation either
rename it locally to the official `GEMINI_API_KEY` convention or support it as a
temporary compatibility alias. Never expose the API key to the frontend, logs,
database, or source control. Fail startup with a clear configuration error if a
required secret is absent.

Model IDs are configuration because Gemini aliases and retirement schedules
change. For repeatable evaluation/deployment, pin a stable model ID after a model
smoke test; do not use a `latest` or preview alias by default.

## 12. Quality and evaluation strategy

Create a versioned gold dataset before tuning retrieval: initially 40–60 real
questions spanning all semesters, including exact-term lookup, conceptual
questions, equations, cross-document synthesis, Turkish/English questions,
unanswerable questions, and adversarial instructions embedded in notes.

Measure separately:

- Retrieval recall@5 and recall@10 against expected documents/pages.
- Mean reciprocal rank and nDCG.
- Citation precision: cited source actually supports the adjacent claim.
- Citation completeness: important claims have citations.
- Groundedness and unanswerable-question refusal rate.
- Answer correctness judged against a rubric.
- p50/p95 retrieval latency and time-to-first-token.
- Per-query generation/embedding token use and estimated cost.
- Ingestion success rate, OCR rate, and extraction-quality distribution.

Every meaningful parser, chunker, embedding, prompt, or model change runs the
same evaluation set and writes a report. Quality gates should prevent a model
upgrade that silently improves prose while reducing source accuracy.

## 13. Security, privacy, and operational constraints

- Treat PDFs/Markdown as untrusted input; never execute embedded code or commands.
- Prevent path traversal by resolving requested document IDs through the catalog,
  never by accepting raw filesystem paths from an API client.
- Restrict served content to the configured corpus root.
- Apply upload/file-size limits if uploads are added later.
- Escape extracted text and model output before rendering.
- Defend against prompt injection by delimiting evidence, declaring it untrusted,
  and allowing citations only from the server-created source registry.
- Redact secrets and document contents from routine logs.
- Add request limits, timeouts, bounded queues, and Gemini retry budgets.
- Back up PostgreSQL metadata/evaluations; the original `data/` corpus remains the
  recoverable source of truth, while `runtime/` stays disposable.
- Confirm the right to process third-party textbooks/lecture material through a
  remote model API before indexing them. Local-only parsing does not mean local-
  only inference.

## 14. Implementation phases and acceptance gates

### Phase 0 — Baseline and contracts

- Initialize Git, dependency manifests, lint/type/test tooling, Docker Compose,
  configuration validation, and ADRs.
- Freeze API schemas, provenance model, and a small seed evaluation set.
- Inventory page counts and identify scanned/encrypted/corrupt PDFs.

Gate: services boot reproducibly; secrets are excluded; corpus inventory report
is deterministic.

### Phase 1 — Catalog and extraction

- Implement discovery, hashing, metadata derivation, PDF/Markdown extraction,
  quality scoring, OCR fallback, persistence, and job status.

Gate: all readable files are cataloged; page numbers round-trip correctly; every
failure is visible and retryable; unchanged files are skipped.

### Phase 2 — Indexing and retrieval

- Implement chunking, Gemini embedding batches, pgvector/FTS indexes, filters,
  RRF fusion, adjacent-context expansion, and retrieval diagnostics.

Gate: target recall@10 is agreed after baseline measurement; every hit maps to an
existing file and valid page; re-indexing is idempotent.

### Phase 3 — Grounded generation

- Implement the Gemini provider, prompt assembly, evidence threshold, structured
  output, source-label validation, SSE, conversations, and telemetry.

Gate: no returned citation can reference a source outside the retrieved context;
unanswerable tests refuse reliably; failures do not leak secrets/context.

### Phase 4 — User interface

- Build chat, scope filters, streaming states, citation drawer, PDF deep links,
  document library, ingestion progress, and failure states.

Gate: a user can ask, inspect evidence, open the cited page, and distinguish an
unsupported answer without developer tools.

### Phase 5 — Hardening and release

- Run corpus-wide ingestion, tune from evaluation evidence, add backups,
  rate/time limits, deployment documentation, and end-to-end tests.

Gate: evaluation thresholds, p95 latency, cost ceiling, recovery test, and threat
checklist all pass on the target deployment machine.

## 15. Key risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Slides, math, diagrams, tables extract poorly | Missing or misleading evidence | Quality scoring, OCR fallback, page previews; later multimodal page retrieval experiment |
| Chunk boundaries destroy context | Weak retrieval/answers | Preserve page/heading boundaries, adjacent expansion, evaluate multiple chunk policies |
| Model invents citations | False trust | Immutable source labels plus server-side citation validation |
| Similar lectures crowd out the correct source | Low precision | Hybrid search, metadata filters, deduplication, diversity and optional reranking |
| Full re-index costs and takes time | Slow iteration | Hashes, versioned pipelines, batch API option, resumable jobs |
| Gemini model changes/deprecates | Outage or quality drift | Provider interface, configurable pinned IDs, smoke tests, evaluation gate |
| API quota/rate limits | Failed ingestion or chat | Bounded concurrency, retry/backoff, checkpoints, usage metrics |
| Remote processing of copyrighted/private notes | Compliance/privacy exposure | Rights review, minimal transmitted context, clear deployment policy; local model adapter later |
| One process handles long ingestion jobs | API instability | Start with durable DB job state; split worker into a separate process when needed |

## 16. Scale path

At this corpus size, avoid Kafka, microservices, Kubernetes, and a dedicated vector
database. They add operational cost without improving the product. The first
scale boundary is separating the worker process and moving original/derived files
to object storage. PostgreSQL/pgvector should remain sufficient well beyond this
corpus if indexes and filters are designed correctly.

If the product becomes multi-tenant, add tenant IDs and row-level authorization
before onboarding the second user; retrofitting ownership after data is shared is
high-risk. If multimodal retrieval materially improves diagram/formula questions,
add a page-image embedding column or separate collection without replacing the
text index.

## 17. Decisions to validate during implementation

These are experiments, not reasons to block scaffolding:

1. Native parser coverage and the percentage of pages requiring OCR.
2. Best chunk size/overlap per retrieval evaluation, not intuition.
3. Whether embedding at 1,536 dimensions meaningfully beats 768 for this corpus.
4. Whether Gemini reranking improves citation precision enough to justify cost.
5. Whether page-image/multimodal retrieval is required for math, circuit, and
   diagram-heavy courses.
6. Exact generation model after a current availability, cost, latency, and quality
   smoke test in the account tied to the API key.

## 18. Official references

- Gemini models: <https://ai.google.dev/gemini-api/docs/models>
- Gemini model deprecations: <https://ai.google.dev/gemini-api/docs/deprecations>
- Gemini embeddings: <https://ai.google.dev/gemini-api/docs/embeddings>
- Gemini File Search: <https://ai.google.dev/gemini-api/docs/file-search>
- Google Gen AI Python SDK: <https://googleapis.github.io/python-genai/>

