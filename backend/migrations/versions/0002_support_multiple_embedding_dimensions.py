"""Support local 1024-dimension and Gemini 1536-dimension embeddings."""

from alembic import op

revision = "0002_embedding_dimensions"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A fixed vector(1536) column would reject Qwen3's 1024-dimension output.
    # Keep the vector space explicit per chunk and index each supported space
    # independently. The provider/model predicates in retrieval make the
    # partial indexes safe and prevent incompatible vectors from being mixed.
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
    op.execute(
        "ALTER TABLE chunks ALTER COLUMN embedding TYPE vector USING embedding::vector"
    )
    op.execute(
        """
        CREATE INDEX ix_chunks_embedding_1024_hnsw
        ON chunks USING hnsw ((embedding::vector(1024)) vector_cosine_ops)
        WHERE embedding_dimension = 1024
        """
    )
    op.execute(
        """
        CREATE INDEX ix_chunks_embedding_1536_hnsw
        ON chunks USING hnsw ((embedding::vector(1536)) vector_cosine_ops)
        WHERE embedding_dimension = 1536
        """
    )


def downgrade() -> None:
    # This intentionally fails if 1024-dimension vectors exist. Losing local
    # embeddings silently is worse than requiring an explicit re-index before
    # a downgrade.
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_1024_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_1536_hnsw")
    op.execute(
        "ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(1536) "
        "USING embedding::vector(1536)"
    )
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw "
        "(embedding vector_cosine_ops)"
    )
