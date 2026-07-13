"""
One-off migration: dense-only "trendlens" collection -> dense+sparse
"trendlens_hybrid" collection, for hybrid (dense + BM25) search.

Qdrant can't add a new named vector to an existing collection in place, so
this backfills into a new collection instead of touching the old one —
blue-green style. The old collection is left untouched; drop it manually
once eval confirms the new one works (see backend/Design.md Iteration log).

No OpenAI calls needed — existing dense vectors are reused as-is via
Qdrant's scroll API (with_vectors=True); only the new BM25 sparse vector
is computed here.

Usage:
    cd backend
    .venv/bin/python scripts/migrate_hybrid_schema.py
"""
import logging
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

from qdrant_client.models import SparseVector, PointStruct

from src.storage.vector_store import get_client, ensure_collection, COLLECTION
from src.ingestion.sparse_embedder import embed_chunks_sparse

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

OLD_COLLECTION = "trendlens"
BATCH_SIZE = 100


def run() -> None:
    client = get_client()
    ensure_collection(client)  # creates COLLECTION ("trendlens_hybrid") if missing

    migrated = 0
    offset = None

    while True:
        points, offset = client.scroll(
            collection_name=OLD_COLLECTION,
            limit=BATCH_SIZE,
            offset=offset,
            with_vectors=True,
            with_payload=True,
        )
        if not points:
            break

        # Reuse the existing dense vector, compute a fresh sparse vector
        # from the stored chunk text — same shape embed_chunks_sparse()
        # expects (a list of dicts with a "text" key).
        chunk_texts = [{"text": p.payload["text"]} for p in points]
        sparse_vectors = embed_chunks_sparse(chunk_texts)

        new_points = [
            PointStruct(
                id=point.id,
                vector={
                    "dense": point.vector,
                    "bm25": SparseVector(
                        indices=sparse["sparse_vector"]["indices"],
                        values=sparse["sparse_vector"]["values"],
                    ),
                },
                payload=point.payload,
            )
            for point, sparse in zip(points, sparse_vectors)
        ]
        client.upsert(collection_name=COLLECTION, points=new_points)

        migrated += len(new_points)
        logger.info("Migrated %d points so far", migrated)

        if offset is None:
            break

    old_count = client.count(collection_name=OLD_COLLECTION).count
    new_count = client.count(collection_name=COLLECTION).count
    logger.info(
        "Done. Old collection '%s': %d points. New collection '%s': %d points.",
        OLD_COLLECTION, old_count, COLLECTION, new_count,
    )
    if old_count != new_count:
        logger.warning("Point count mismatch — investigate before dropping the old collection.")


if __name__ == "__main__":
    run()
