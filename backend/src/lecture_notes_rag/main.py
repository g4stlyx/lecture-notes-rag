from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lecture_notes_rag.api.routes import chat, documents, health, ingestion
from lecture_notes_rag.core.logging import configure_logging
from lecture_notes_rag.core.settings import get_settings
from lecture_notes_rag.workers.recovery import recover_interrupted_ingestion_jobs


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    settings.resolved_runtime_root.mkdir(parents=True, exist_ok=True)
    try:
        recover_interrupted_ingestion_jobs()
    except Exception:
        # The health endpoint will expose an unavailable database; do not make
        # local startup impossible solely because recovery could not run.
        import logging

        logging.getLogger(__name__).exception("Could not recover interrupted ingestion jobs")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Lecture Notes RAG API",
        version="0.1.0",
        description="Private, citation-first question answering over lecture notes.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(documents.router, prefix=settings.api_prefix)
    app.include_router(ingestion.router, prefix=settings.api_prefix)
    app.include_router(chat.router, prefix=settings.api_prefix)
    return app


app = create_app()
