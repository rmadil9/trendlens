import logging
import os
from datetime import datetime, timezone, timedelta

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    Range,
    Prefetch,
    FusionQuery,
    Fusion,
    SparseVector,
)

from src.ingestion.embedder import embed_text
from src.ingestion.sparse_embedder import embed_text_sparse
from src.retrieval.reranker import rerank
from src.storage.vector_store import COLLECTION

logger = logging.getLogger(__name__)

# Final number of chunks handed to generation — applied by the reranker,
# after fusion, not by Qdrant directly.
K = int(os.getenv("RETRIEVAL_K", "5"))

# How many fused candidates to pull before reranking narrows to K. Wider
# than K so the reranker has real material to choose between.
CANDIDATES = int(os.getenv("RETRIEVAL_CANDIDATES", "20"))

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
    Hybrid retrieval: embed the question both densely (semantic) and sparsely
    (BM25 keyword), search both legs inside Qdrant, fuse them server-side
    with RRF, then rerank the fused candidates and cut to k.

    The time filter runs INSIDE each prefetch leg (not post-filtered in
    Python) — same reasoning as before: guarantees results from the correct
    window instead of risking 0 if the top candidates were all old.

    Returns a list of chunk dicts (text, title, url, source, published_at,
    score, rerank_score). Returns [] if no chunks exist in the time window.
    """
    cutoff = _cutoff_timestamp(time_window)

    time_filter = Filter(
        must=[
            FieldCondition(
                key="published_at",
                range=Range(gte=cutoff),  # gte = greater than or equal
            )
        ]
    )

    # Same question, embedded two ways — dense for semantic similarity,
    # sparse for exact keyword/named-entity matches dense embeddings miss.
    dense_vector = embed_text(question)
    sparse_vector = embed_text_sparse(question)

    response = client.query_points(
        collection_name=COLLECTION,
        prefetch=[
            Prefetch(
                query=dense_vector,
                using="dense",
                filter=time_filter,
                limit=CANDIDATES,
            ),
            Prefetch(
                query=SparseVector(
                    indices=sparse_vector["indices"],
                    values=sparse_vector["values"],
                ),
                using="bm25",
                filter=time_filter,
                limit=CANDIDATES,
            ),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=CANDIDATES,
        with_payload=True,
    )

    if not response.points:
        logger.warning("No chunks found in window=%s for: %r", time_window, question)
        return []

    chunks = []
    for hit in response.points:
        chunk = dict(hit.payload)   # extract text, title, url, source, published_at
        chunk["score"] = hit.score  # RRF fusion score — useful for debugging
        chunks.append(chunk)

    logger.info("Fused %d candidates, reranking to top %d", len(chunks), k)
    return rerank(question, chunks, top_k=k)
