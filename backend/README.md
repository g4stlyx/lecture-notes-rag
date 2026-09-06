# Lecture Notes RAG API

Run from this directory after copying the root environment configuration:

```powershell
uv sync --all-groups
uv run alembic upgrade head
uv run uvicorn lecture_notes_rag.main:app --reload --port 8000
```

The API expects PostgreSQL with the pgvector extension. Start the local database
from the repository root with `docker compose up -d postgres`.

