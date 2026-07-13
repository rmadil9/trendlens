"""
Day 2 test suite — chunker, embedder, vector store.
Run: cd backend && .venv/bin/python -m pytest tests/test_day2.py -v
"""
import os
import sys
import pytest

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

from src.storage.article_store import Article
from src.ingestion.chunker import chunk_article
from src.ingestion.embedder import embed_chunks, DIMENSIONS
from src.ingestion.sparse_embedder import embed_chunks_sparse
from src.storage.vector_store import get_client, ensure_collection, upsert_chunks, COLLECTION


# ── shared fixture ────────────────────────────────────────────────────────────

def make_article(raw_text: str) -> Article:
    return Article(
        url="https://example.com/test-article",
        title="Test Article",
        source="TestFeed",
        published_at="2024-06-27T00:00:00Z",
        raw_text=raw_text,
    )


SHORT_TEXT = "This is a short article. " * 10          # ~50 words — fits in one chunk
LONG_TEXT  = "Federal Reserve raises interest rates. " * 600   # ~1800 words — multiple chunks


# ── chunker tests ─────────────────────────────────────────────────────────────

class TestChunker:

    def test_short_article_produces_one_chunk(self):
        chunks = chunk_article(make_article(SHORT_TEXT))
        assert len(chunks) == 1

    def test_long_article_produces_multiple_chunks(self):
        chunks = chunk_article(make_article(LONG_TEXT))
        assert len(chunks) > 1

    def test_chunk_size_under_limit(self):
        chunks = chunk_article(make_article(LONG_TEXT))
        for c in chunks:
            word_count = len(c["text"].split())
            assert word_count <= 550, f"Chunk too large: {word_count} words"

    def test_chunk_index_is_sequential(self):
        chunks = chunk_article(make_article(LONG_TEXT))
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_metadata_fields_present(self):
        chunks = chunk_article(make_article(SHORT_TEXT))
        required = {"text", "source", "title", "url", "published_at", "chunk_index"}
        for c in chunks:
            assert required.issubset(c.keys()), f"Missing keys: {required - c.keys()}"

    def test_published_at_is_integer(self):
        chunks = chunk_article(make_article(SHORT_TEXT))
        for c in chunks:
            assert isinstance(c["published_at"], int), "published_at must be a Unix timestamp (int)"

    def test_published_at_correct_value(self):
        chunks = chunk_article(make_article(SHORT_TEXT))
        # 2024-06-27T00:00:00Z → 1719446400
        assert chunks[0]["published_at"] == 1719446400

    def test_empty_article_produces_no_chunks(self):
        chunks = chunk_article(make_article(""))
        assert len(chunks) == 0


# ── embedder tests ────────────────────────────────────────────────────────────

class TestEmbedder:

    def test_vector_dimension_is_1536(self):
        chunks = chunk_article(make_article(SHORT_TEXT))
        embedded = embed_chunks(chunks)
        assert len(embedded[0]["embedding"]) == DIMENSIONS

    def test_embedding_key_added_to_chunk(self):
        chunks = chunk_article(make_article(SHORT_TEXT))
        embedded = embed_chunks(chunks)
        for c in embedded:
            assert "embedding" in c

    def test_chunk_count_unchanged_after_embedding(self):
        chunks = chunk_article(make_article(LONG_TEXT))
        original_count = len(chunks)
        embedded = embed_chunks(chunks)
        assert len(embedded) == original_count

    def test_embedding_values_are_floats(self):
        chunks = chunk_article(make_article(SHORT_TEXT))
        embedded = embed_chunks(chunks)
        vector = embedded[0]["embedding"]
        assert all(isinstance(v, float) for v in vector)


# ── vector store tests ────────────────────────────────────────────────────────

class TestVectorStore:

    @pytest.fixture(autouse=True)
    def client(self):
        self.qdrant = get_client()
        ensure_collection(self.qdrant)

    def _embed_article(self, text: str) -> list[dict]:
        chunks = chunk_article(make_article(text))
        chunks = embed_chunks(chunks)
        return embed_chunks_sparse(chunks)

    def test_collection_exists_after_ensure(self):
        names = [c.name for c in self.qdrant.get_collections().collections]
        assert COLLECTION in names

    def test_upsert_adds_points(self):
        before = self.qdrant.get_collection(COLLECTION).points_count
        embedded = self._embed_article(SHORT_TEXT)
        upsert_chunks(self.qdrant, embedded)
        after = self.qdrant.get_collection(COLLECTION).points_count
        assert after >= before + len(embedded)

    def test_upsert_is_idempotent(self):
        """Upserting the same chunks twice must not increase the point count."""
        embedded = self._embed_article(SHORT_TEXT)
        upsert_chunks(self.qdrant, embedded)
        count_after_first = self.qdrant.get_collection(COLLECTION).points_count

        upsert_chunks(self.qdrant, embedded)
        count_after_second = self.qdrant.get_collection(COLLECTION).points_count

        assert count_after_first == count_after_second, "Duplicate points were inserted"

    def test_ensure_collection_is_safe_to_call_twice(self):
        # Should not raise even if collection already exists
        ensure_collection(self.qdrant)
        ensure_collection(self.qdrant)
