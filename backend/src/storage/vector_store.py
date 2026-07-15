import logging
import os

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams

from src.ingestion.embedder import DIMENSIONS

logger = logging.getLogger(__name__)

# Points at the dense+sparse hybrid collection created by
# scripts/migrate_hybrid_schema.py — the old dense-only "trendlens"
# collection is left in place until the migration is verified via eval.
COLLECTION = os.getenv("QDRANT_COLLECTION", "trendlens_hybrid")

_client: QdrantClient | None = None


def get_client(
    host: str = os.getenv("QDRANT_HOST", "localhost"),
    port: int = int(os.getenv("QDRANT_PORT", "6333")),
) -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=host, port=port)
    return _client


def ensure_collection(client: QdrantClient) -> None:
    """Create the collection if it doesn't exist. Safe to call on every startup."""
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION in existing:
        logger.info("Collection '%s' already exists — skipping creation", COLLECTION)
        return

    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={
            "dense": VectorParams(
                size=DIMENSIONS,      # must match embedding model output exactly (1536)
                distance=Distance.COSINE,  # angle-based similarity — right for semantic search
            ),
        },
        sparse_vectors_config={
            "bm25": SparseVectorParams(),  # keyword-match leg of hybrid search
        },
    )
    logger.info("Created collection '%s' (dense=%d/COSINE, sparse=bm25)", COLLECTION, DIMENSIONS)
