import logging
import os
from datetime import datetime, timezone, timedelta

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, Range

from src.ingestion.embedder import embed_text
from src.storage.vector_store import COLLECTION

logger = logging.getLogger(__name__)

K = int(os.getenv("RETRIEVAL_K", "5"))

# Explicit day counts for each UI time-window chip. Replaces the old
# keyword-sniffing of the question text (parse_time_window) now that the
# frontend sends the window directly — keeping both would let a stray
# "this week" inside the question text silently override the chip the
# user actually selected.
WINDOW_DAYS = {
    "today": 1,
    "week": 7,
    "month": 30,
}


def _cutoff_timestamp(time_window: str) -> int:
    days = WINDOW_DAYS.get(time_window, WINDOW_DAYS["today"])
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=days)
    logger.info("Time window: %s (last %d days, cutoff: %s)", time_window, days, cutoff.isoformat())
    return int(cutoff.timestamp())


def retrieve(question: str, client: QdrantClient, time_window: str = "today", k: int = K) -> list[dict]:
    """
    Embed the question, then search Qdrant for the K most relevant chunks
    that were published within the given time window.

    The filter runs INSIDE Qdrant (not post-filtering in Python).
    This guarantees we always get up to K results from the correct window —
    post-filtering could silently return 0 results if all top-K were old.

    Returns a list of chunk dicts (text, title, url, source, published_at, score).
    Returns [] if no chunks exist in the time window — caller handles this.
    """
    cutoff = _cutoff_timestamp(time_window)

    # Embed the question — must use the same model used during ingestion
    # so the question vector lives in the same 1536-dimensional space
    query_vector = embed_text(question)

    # The filter narrows the search space BEFORE similarity is computed
    time_filter = Filter(
        must=[
            FieldCondition(
                key="published_at",
                range=Range(gte=cutoff),  # gte = greater than or equal
            )
        ]
    )

    results = client.search(
        collection_name=COLLECTION,
        query_vector=query_vector,
        query_filter=time_filter,
        limit=k,
        with_payload=True,   # return the payload (text, title, url, etc.) not just the ID
    )

    if not results:
        logger.warning("No chunks found in window=%s for: %r", time_window, question)
        return []

    chunks = []
    for hit in results:
        chunk = dict(hit.payload)   # extract text, title, url, source, published_at
        chunk["score"] = hit.score  # cosine similarity score — useful for debugging
        chunks.append(chunk)

    logger.info("Retrieved %d chunks (top score: %.3f)", len(chunks), chunks[0]["score"])
    return chunks
