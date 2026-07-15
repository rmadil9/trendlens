import logging
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, SparseVector

from src.storage.vector_store import COLLECTION

logger = logging.getLogger(__name__)


def upsert_chunks(client: QdrantClient, chunks: list[dict]) -> None:
    """Write embedded chunks to Qdrant. Idempotent — same chunk upserted twice is a no-op."""
    points = [_to_point(c) for c in chunks]

    client.upsert(collection_name=COLLECTION, points=points)
    logger.info("Upserted %d points into '%s'", len(points), COLLECTION)


def _to_point(chunk: dict) -> PointStruct:
    # Deterministic UUID from url + chunk_index — same chunk always gets the same ID
    # This makes upsert idempotent: re-running the pipeline won't duplicate vectors
    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, chunk["url"] + str(chunk["chunk_index"])))

    return PointStruct(
        id=point_id,
        vector={
            "dense": chunk["embedding"],
            "bm25": SparseVector(
                indices=chunk["sparse_vector"]["indices"],
                values=chunk["sparse_vector"]["values"],
            ),
        },
        payload={                       # everything except the raw vector lives here
            "text": chunk["text"],      # stored so retrieval can return the actual passage
            "source": chunk["source"],
            "title": chunk["title"],
            "url": chunk["url"],
            "published_at": chunk["published_at"],   # Unix int — enables range filtering
            "chunk_index": chunk["chunk_index"],
        },
    )
