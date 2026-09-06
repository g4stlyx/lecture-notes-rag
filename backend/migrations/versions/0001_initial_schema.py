"""Create the citation-first RAG schema."""

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE documents (
            id uuid PRIMARY KEY,
            source_path varchar(1024) NOT NULL UNIQUE,
            display_name varchar(512) NOT NULL,
            extension varchar(16) NOT NULL,
            mime_type varchar(128) NOT NULL,
            semester integer,
            course varchar(255),
            content_hash varchar(64) NOT NULL,
            size_bytes integer NOT NULL,
            modified_at timestamptz NOT NULL,
            page_count integer,
            language varchar(32),
            extraction_method varchar(32),
            extraction_quality double precision,
            pipeline_version varchar(32) NOT NULL DEFAULT '1',
            status varchar(32) NOT NULL DEFAULT 'discovered',
            error_code varchar(128),
            error_detail text,
            indexed_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_documents_semester ON documents (semester)")
    op.execute("CREATE INDEX ix_documents_course ON documents (course)")
    op.execute("CREATE INDEX ix_documents_content_hash ON documents (content_hash)")
    op.execute("CREATE INDEX ix_documents_status ON documents (status)")
    op.execute(
        """
        CREATE TABLE pages (
            id uuid PRIMARY KEY,
            document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            page_number integer NOT NULL,
            text text NOT NULL,
            heading varchar(512),
            extraction_method varchar(32) NOT NULL,
            extraction_quality double precision NOT NULL,
            artifact_path varchar(1024),
            content_hash varchar(64) NOT NULL,
            CONSTRAINT uq_pages_document_page UNIQUE (document_id, page_number)
        )
        """
    )
    op.execute("CREATE INDEX ix_pages_document_id ON pages (document_id)")
    op.execute(
        """
        CREATE TABLE chunks (
            id uuid PRIMARY KEY,
            document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            page_start integer NOT NULL,
            page_end integer NOT NULL,
            section_heading varchar(512),
            chunk_index integer NOT NULL,
            text text NOT NULL,
            token_count integer NOT NULL,
            content_hash varchar(64) NOT NULL,
            parser_version varchar(32) NOT NULL DEFAULT '1',
            chunker_version varchar(32) NOT NULL DEFAULT '1',
            embedding vector(1536),
            embedding_model varchar(128),
            embedding_dimension integer,
            search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED,
            CONSTRAINT uq_chunks_document_index UNIQUE (document_id, chunk_index)
        )
        """
    )
    op.execute("CREATE INDEX ix_chunks_document_id ON chunks (document_id)")
    op.execute("CREATE INDEX ix_chunks_search_vector ON chunks USING gin (search_vector)")
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        """
        CREATE TABLE ingestion_jobs (
            id uuid PRIMARY KEY,
            status varchar(32) NOT NULL DEFAULT 'queued',
            force boolean NOT NULL DEFAULT false,
            discovered_count integer NOT NULL DEFAULT 0,
            processed_count integer NOT NULL DEFAULT 0,
            skipped_count integer NOT NULL DEFAULT 0,
            failed_count integer NOT NULL DEFAULT 0,
            started_at timestamptz,
            completed_at timestamptz,
            error_summary text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_ingestion_jobs_status ON ingestion_jobs (status)")
    op.execute(
        """
        CREATE TABLE conversations (
            id uuid PRIMARY KEY,
            title varchar(512),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE messages (
            id uuid PRIMARY KEY,
            conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role varchar(16) NOT NULL,
            text text NOT NULL,
            filters jsonb,
            retrieved_chunk_ids jsonb,
            sources jsonb,
            model varchar(128),
            latency_ms integer,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_messages_conversation_id ON messages (conversation_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS conversations")
    op.execute("DROP TABLE IF EXISTS ingestion_jobs")
    op.execute("DROP TABLE IF EXISTS chunks")
    op.execute("DROP TABLE IF EXISTS pages")
    op.execute("DROP TABLE IF EXISTS documents")
