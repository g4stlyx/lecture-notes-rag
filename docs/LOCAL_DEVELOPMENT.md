# Local development

## Prerequisites

- Docker Desktop running.
- `uv` for the Python backend.
- Node.js 22+ for the React client.
- Ollama running locally with `qwen3-embedding:0.6b` pulled.
- A Gemini API key in the root `.env` file only if you want generated chat answers.

## One-time setup

1. Copy `.env.example` to `.env` if you do not already have one. Keep the
   existing `GEMINI_API_KEY` value private. The default embedding provider is
   local Ollama/Qwen, using 1,024-dimensional vectors.
2. Keep `POSTGRES_*` and `DATABASE_URL` consistent. The development defaults
   already match each other.
3. Start the database from the repository root:

   ```powershell
   docker compose up -d postgres
   ```

4. Install backend dependencies and create the schema:

   ```powershell
   Set-Location backend
   uv sync --all-groups
   uv run alembic upgrade head
   ```

5. Install frontend dependencies:

   ```powershell
   Set-Location ../frontend
   npm install
   ```

## Run locally

Use two terminals.

```powershell
# Terminal 1, repository/backend
uv run uvicorn lecture_notes_rag.main:app --reload --port 8000
```

```powershell
# Terminal 2, repository/frontend
npm run dev
```

Open `http://127.0.0.1:5173`. Confirm `/api/v1/health` reports `status: ok`
before selecting **Index corpus**. Indexing uses the local Ollama model by
default, so document embeddings never leave your machine and do not consume a
Gemini quota. Confirm the local model is available first:

```powershell
ollama list
ollama run qwen3-embedding:0.6b "embedding health check"
```

Changing the embedding provider or embedding dimension always requires a full
re-index. The application automatically reprocesses every document and excludes
the previous vector space from retrieval until that work is complete; do not mix
vectors created by different embedding models.

To use Gemini embeddings instead, set `EMBEDDING_PROVIDER=gemini` and
`EMBEDDING_DIMENSION=1536`. Gemini embedding ingestion is rate-limited. If the
provider returns a quota response without a usable retry window, the job is shown
as **paused** instead of failing the rest of the corpus.

In local development, ingestion runs inside the API process. Stopping Uvicorn
interrupts that work; on the next backend startup, unfinished jobs are marked
**interrupted** automatically. Start a new non-force indexing job to resume.

## Verification commands

```powershell
Set-Location backend
uv run ruff check .
uv run pytest -q

Set-Location ../frontend
npm run build
```

## OCR

The ingestion service detects weak native PDF extraction and tries OCRmyPDF when
it is available on `PATH`. Install OCRmyPDF plus Tesseract before running a
corpus with scans. Without it, readable native PDF text is still indexed and
weak/scanned documents remain visible through their extraction quality/status.
