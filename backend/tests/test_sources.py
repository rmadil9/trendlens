"""
Unit tests for source deduplication — deterministic, no external services.
Run: cd backend && .venv/bin/python -m pytest tests/test_sources.py -v
"""
import sys

sys.path.insert(0, ".")

from src.retrieval.sources import dedupe_sources


class TestDedupeSources:

    def test_dedupes_same_url(self):
        chunks = [
            {"url": "https://a.com/1", "title": "A", "source": "Feed", "published_at": 100},
            {"url": "https://a.com/1", "title": "A", "source": "Feed", "published_at": 100},
            {"url": "https://a.com/1", "title": "A", "source": "Feed", "published_at": 100},
        ]
        result = dedupe_sources(chunks)
        assert len(result) == 1

    def test_preserves_first_seen_order(self):
        chunks = [
            {"url": "https://b.com", "title": "B", "source": "Feed", "published_at": 200},
            {"url": "https://a.com", "title": "A", "source": "Feed", "published_at": 100},
            {"url": "https://c.com", "title": "C", "source": "Feed", "published_at": 300},
        ]
        result = dedupe_sources(chunks)
        assert [s["url"] for s in result] == [
            "https://b.com",
            "https://a.com",
            "https://c.com",
        ]

    def test_different_urls_all_kept(self):
        chunks = [
            {"url": f"https://example.com/{i}", "title": f"T{i}", "source": "F", "published_at": i}
            for i in range(3)
        ]
        result = dedupe_sources(chunks)
        assert len(result) == 3

    def test_empty_input_returns_empty(self):
        assert dedupe_sources([]) == []

    def test_output_has_required_fields(self):
        chunks = [
            {"url": "https://x.com", "title": "X", "source": "S", "published_at": 99},
        ]
        result = dedupe_sources(chunks)
        required = {"title", "url", "source", "published_at"}
        assert required.issubset(result[0].keys())
