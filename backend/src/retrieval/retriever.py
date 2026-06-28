import logging
from datetime import datetime, timezone, timedelta

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, Range

from src.ingestion.embedder import _get_client as _get_openai, MODEL
from src.storage.vector_store import COLLECTION

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_DAYS = 30
K = 5


def parse_time_window(question: str) -> int:
    """
    Scan the question for time keywords and return a Unix timestamp cutoff.
    Anything published before this timestamp is excluded from search.

    'this week'  → 7 days ago
    'this month' → 30 days ago
    default      → DEFAULT_WINDOW_DAYS ago

    Why keywords-in-question and not a separate argument?
    Because the user types 'what's new in AI this week?' and we want that
    to work without forcing them to pass --window=7 separately.
    Tradeoff: brittle for unusual phrasing, but good enough for a demo.
    """
    q = question.lower()
    now = datetime.now(tz=timezone.utc)

    if "this week" in q or "past week" in q or "last week" in q:
        days = 7
    elif "this month" in q or "past month" in q or "last month" in q:
        days = 30
    elif "today" in q:
        days = 1
    else:
        days = DEFAULT_WINDOW_DAYS

    cutoff = now - timedelta(days=days)
    logger.info("Time window: last %d days (cutoff: %s)", days, cutoff.isoformat())
    return int(cutoff.timestamp())


def retrieve(question: str, client: QdrantClient, k: int = K) -> list[dict]:
    """
    Embed the question, then search Qdrant for the K most relevant chunks
    that were published within the time window parsed from the question.

    The filter runs INSIDE Qdrant (not post-filtering in Python).
    This guarantees we always get up to K results from the correct window —
    post-filtering could silently return 0 results if all top-K were old.

    Returns a list of chunk dicts (text, title, url, source, published_at, score).
    Returns [] if no chunks exist in the time window — caller handles this.
    """
    cutoff = parse_time_window(question)

    # Embed the question — must use the same model used during ingestion
    # so the question vector lives in the same 1536-dimensional space
    openai = _get_openai()
    response = openai.embeddings.create(model=MODEL, input=[question])
    query_vector = response.data[0].embedding

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
        logger.warning("No chunks found in the last %d-day window for: %r", DEFAULT_WINDOW_DAYS, question)
        return []

    chunks = []
    for hit in results:
        chunk = dict(hit.payload)   # extract text, title, url, source, published_at
        chunk["score"] = hit.score  # cosine similarity score — useful for debugging
        chunks.append(chunk)

    logger.info("Retrieved %d chunks (top score: %.3f)", len(chunks), chunks[0]["score"])
    return chunks
