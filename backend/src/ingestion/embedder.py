import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

MODEL = "text-embedding-3-small"
DIMENSIONS = 1536        # fixed output size for this model — Qdrant collection must match
BATCH_SIZE = 100         # OpenAI allows up to 2048 inputs per call; 100 is safe and cheap


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    # Lazy init — avoids reading env var at import time, which breaks tests
    global _client
    if _client is None:
        _client = OpenAI()   # reads OPENAI_API_KEY from environment automatically
    return _client


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Add an 'embedding' key (list[float], len=1536) to each chunk dict.
    Sends texts in batches to stay within API limits.
    Returns the same chunks with embeddings attached.
    """
    texts = [c["text"] for c in chunks]
    vectors = _embed_texts(texts)

    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector

    return chunks


def _embed_texts(texts: list[str]) -> list[list[float]]:
    """Call the API in batches, return flat list of vectors in the same order."""
    client = _get_client()
    all_vectors = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        response = client.embeddings.create(model=MODEL, input=batch)

        # response.data is a list sorted by index — safe to extend in order
        all_vectors.extend([item.embedding for item in response.data])
        logger.debug("Embedded batch %d-%d (%d tokens used)",
                     i, i + len(batch), response.usage.total_tokens)

    return all_vectors
