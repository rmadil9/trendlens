"""
Hybrid search + reranking test suite — sparse embedder, dual-vector point
construction, and reranker ordering.
Run: cd backend && .venv/bin/python -m pytest tests/test_hybrid.py -v
"""
import sys
import pytest

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

from src.ingestion.sparse_embedder import embed_text_sparse, embed_chunks_sparse
from src.storage.vector_store import _to_point
from src.retrieval.reranker import rerank


# ── sparse embedder tests ───────────────────────────────────────────────────

class TestSparseEmbedder:

    def test_query_embed_returns_indices_and_values(self):
        result = embed_text_sparse("Anthropic Claude AI model")
        assert "indices" in result and "values" in result
        assert len(result["indices"]) == len(result["values"])
        assert len(result["indices"]) > 0

    def test_chunk_embed_adds_sparse_vector_key(self):
        chunks = [{"text": "Sony discontinues PlayStation physical game discs"}]
        embedded = embed_chunks_sparse(chunks)
        assert "sparse_vector" in embedded[0]
        assert "indices" in embedded[0]["sparse_vector"]
        assert "values" in embedded[0]["sparse_vector"]

    def test_chunk_count_unchanged_after_sparse_embedding(self):
        chunks = [{"text": "chunk one"}, {"text": "chunk two"}]
        embedded = embed_chunks_sparse(chunks)
        assert len(embedded) == 2


# ── vector_store point construction ─────────────────────────────────────────

class TestToPoint:

    def test_point_has_dense_and_sparse_named_vectors(self):
        chunk = {
            "url": "https://example.com/a",
            "chunk_index": 0,
            "text": "some text",
            "source": "TestFeed",
            "title": "Test",
            "published_at": 1719446400,
            "embedding": [0.1] * 1536,
            "sparse_vector": {"indices": [1, 5, 9], "values": [0.5, 0.3, 0.1]},
        }
        point = _to_point(chunk)
        assert "dense" in point.vector
        assert "bm25" in point.vector
        assert point.vector["dense"] == chunk["embedding"]
        assert list(point.vector["bm25"].indices) == chunk["sparse_vector"]["indices"]
        assert list(point.vector["bm25"].values) == chunk["sparse_vector"]["values"]


# ── reranker tests ───────────────────────────────────────────────────────────

class TestReranker:

    def test_relevant_chunk_ranks_above_offtopic_chunk(self):
        question = "What did Anthropic say about Claude cloning?"
        chunks = [
            {"text": "Europe braces for a record-breaking summer heat wave this week."},
            {"text": "Anthropic said it is investigating reports that Alibaba cloned "
                      "Claude's behavior patterns without authorization."},
        ]
        result = rerank(question, chunks, top_k=2)
        assert "Anthropic" in result[0]["text"]

    def test_top_k_limits_result_count(self):
        question = "What's new in AI?"
        chunks = [{"text": f"AI news chunk number {i}"} for i in range(5)]
        result = rerank(question, chunks, top_k=2)
        assert len(result) == 2

    def test_empty_chunks_returns_empty(self):
        assert rerank("any question", [], top_k=5) == []
