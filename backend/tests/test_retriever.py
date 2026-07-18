"""
Retriever tests — unit tests for cutoff logic + integration tests for
end-to-end hybrid retrieval (dense + sparse + RRF + rerank).

Unit:        cd backend && .venv/bin/python -m pytest tests/test_retriever.py -m "not integration" -v
Integration: cd backend && .venv/bin/python -m pytest tests/test_retriever.py -m "integration" -v
"""
import sys
import time
from datetime import datetime, timezone, timedelta

import pytest

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

from src.retrieval.retriever import _cutoff_timestamp, retrieve, WINDOW_DAYS


# ── unit tests — cutoff timestamp logic (deterministic, no services) ─────────

class TestCutoffTimestamp:

    def test_today_is_1_day_ago(self):
        cutoff = _cutoff_timestamp("today")
        expected = int((datetime.now(tz=timezone.utc) - timedelta(days=1)).timestamp())
        # Allow 2-second tolerance for test execution time
        assert abs(cutoff - expected) <= 2

    def test_week_is_7_days_ago(self):
        cutoff = _cutoff_timestamp("week")
        expected = int((datetime.now(tz=timezone.utc) - timedelta(days=7)).timestamp())
        assert abs(cutoff - expected) <= 2

    def test_month_is_30_days_ago(self):
        cutoff = _cutoff_timestamp("month")
        expected = int((datetime.now(tz=timezone.utc) - timedelta(days=30)).timestamp())
        assert abs(cutoff - expected) <= 2

    def test_unknown_window_defaults_to_today(self):
        cutoff_unknown = _cutoff_timestamp("blah")
        cutoff_today = _cutoff_timestamp("today")
        assert abs(cutoff_unknown - cutoff_today) <= 2

    def test_all_window_keys_are_covered(self):
        """Sanity check that every key in WINDOW_DAYS produces a valid timestamp."""
        for window in WINDOW_DAYS:
            cutoff = _cutoff_timestamp(window)
            assert isinstance(cutoff, int)
            assert cutoff > 0


# ── integration tests — end-to-end hybrid retrieval ──────────────────────────
# Requires: Qdrant running, OPENAI_API_KEY set.

@pytest.mark.integration
class TestHybridRetrieveE2E:
    """
    Seeds Qdrant with a small set of known chunks, then runs the full
    retrieve() pipeline: embed question (dense + sparse) → dual-vector
    Qdrant query with RRF fusion → cross-encoder rerank → top-k.
    """

    @pytest.fixture(autouse=True)
    def seed_qdrant(self):
        """Insert known chunks so retrieve() has material to search."""
        from src.storage.vector_store import get_client, ensure_collection
        from src.storage.chunk_store import upsert_chunks
        from src.ingestion.embedder import embed_chunks
        from src.ingestion.sparse_embedder import embed_chunks_sparse

        self.client = get_client()
        ensure_collection(self.client)

        # Current timestamp ensures these chunks fall inside any time window
        now_ts = int(datetime.now(tz=timezone.utc).timestamp())

        self.ai_chunk = {
            "text": "OpenAI released GPT-5 with multimodal reasoning capabilities "
                    "that surpass previous models in coding and scientific benchmarks.",
            "source": "TestFeed",
            "title": "GPT-5 Released",
            "url": "https://test-retrieve.example.com/ai-article",
            "published_at": now_ts,
            "chunk_index": 0,
        }
        self.sports_chunk = {
            "text": "Manchester United signed a new striker from the Brazilian "
                    "league for a record-breaking transfer fee this summer.",
            "source": "TestFeed",
            "title": "Football Transfer News",
            "url": "https://test-retrieve.example.com/sports-article",
            "published_at": now_ts,
            "chunk_index": 0,
        }
        self.old_chunk = {
            "text": "Ancient computing history from the 1960s mainframe era.",
            "source": "TestFeed",
            "title": "Mainframe History",
            "url": "https://test-retrieve.example.com/old-article",
            "published_at": 0,  # Unix epoch — will fail any time window filter
            "chunk_index": 0,
        }

        chunks = [self.ai_chunk, self.sports_chunk, self.old_chunk]
        chunks = embed_chunks(chunks)
        chunks = embed_chunks_sparse(chunks)
        upsert_chunks(self.client, chunks)

        # Small delay to let Qdrant index the points
        time.sleep(0.5)

    def test_relevant_chunk_ranks_above_offtopic(self):
        results = retrieve(
            "What's new in AI and GPT models?",
            self.client,
            time_window="month",
            k=2,
        )
        assert len(results) >= 1
        assert "GPT" in results[0]["text"] or "OpenAI" in results[0]["text"]

    def test_respects_top_k(self):
        results = retrieve(
            "Tell me the latest news",
            self.client,
            time_window="month",
            k=1,
        )
        assert len(results) <= 1

    def test_results_carry_score_and_rerank_score(self):
        results = retrieve(
            "AI model releases",
            self.client,
            time_window="month",
            k=2,
        )
        for chunk in results:
            assert "score" in chunk, "Missing RRF fusion score"
            assert "rerank_score" in chunk, "Missing cross-encoder rerank score"

    def test_old_chunks_excluded_by_time_window(self):
        results = retrieve(
            "mainframe computing history",
            self.client,
            time_window="today",
            k=5,
        )
        # The old chunk (published_at=0) should be filtered out by the time window
        for chunk in results:
            assert chunk.get("url") != "https://test-retrieve.example.com/old-article", \
                "Old chunk should have been excluded by time filter"
