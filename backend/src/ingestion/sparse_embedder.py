import logging
from fastembed import SparseTextEmbedding
logger = logging.getLogger(__name__)
MODEL = "Qdrant/bm25"
_model: SparseTextEmbedding | None = None


def _get_model() -> SparseTextEmbedding:
    # Lazy init — same reasoning as embedder._get_client(): avoids loading
    # the model at import time, which breaks tests that don't need it.
    global _model
    if _model is None:
        _model = SparseTextEmbedding(model_name=MODEL)
    return _model


def embed_text_sparse(text: str) -> dict:
    """Sparse-embed a single string (a user question) for query-time search.

    BM25 scores queries and documents differently (query side uses IDF only,
    document side uses term frequency), so fastembed exposes separate
    query_embed()/embed() entry points — mixing them up produces a
    technically-valid but poorly-scored sparse vector.
    """
    model = _get_model()
    result = next(model.query_embed(text))
    return {"indices": result.indices.tolist(), "values": result.values.tolist()}


def embed_chunks_sparse(chunks: list[dict]) -> list[dict]:
    """Add a 'sparse_vector' key (dict with indices/values) to each chunk —
    same shape/signature convention as embedder.embed_chunks()."""
    model = _get_model()
    texts = [c["text"] for c in chunks]

    for chunk, result in zip(chunks, model.embed(texts)):
        chunk["sparse_vector"] = {
            "indices": result.indices.tolist(),
            "values": result.values.tolist(),
        }

    return chunks


