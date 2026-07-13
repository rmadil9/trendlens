import logging
import os

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

RERANK_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

_model: CrossEncoder | None = None


def _get_model() -> CrossEncoder:
    # Lazy init — same reasoning as embedder._get_client(): avoids loading
    # the model at import time, which breaks tests that don't need it.
    global _model
    if _model is None:
        _model = CrossEncoder(RERANK_MODEL)
    return _model


def rerank(question: str, chunks: list[dict], top_k: int) -> list[dict]:
    """
    Score each (question, chunk text) pair jointly with a cross-encoder —
    more accurate than the fused RRF ordering, which only ranks by position
    in two independent single-vector searches. Returns the top_k chunks,
    each carrying an added 'rerank_score' field alongside the existing
    fusion 'score'.

    Precision pass only — cannot recover chunks that weren't in the fused
    candidate list to begin with.
    """
    if not chunks:
        return chunks

    model = _get_model()
    pairs = [(question, chunk["text"]) for chunk in chunks]
    scores = model.predict(pairs)

    for chunk, score in zip(chunks, scores):
        chunk["rerank_score"] = float(score)

    chunks.sort(key=lambda c: c["rerank_score"], reverse=True)
    return chunks[:top_k]
