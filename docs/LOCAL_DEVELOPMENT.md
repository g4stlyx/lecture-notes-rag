# Local development

## Prerequisites

- Docker Desktop running.
- `uv` for the Python backend.
- Node.js 22+ for the React client.
- A Gemini API key in the root `.env` file.

## One-time setup

1. Copy `.env.example` to `.env` if you do not already have one. Keep the
   existing `GEMINI_API_KEY` value private.
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
before selecting **Index corpus**. Indexing sends chunk text to Gemini to create
embeddings and will consume API quota; it is deliberately never triggered at
application startup.

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

