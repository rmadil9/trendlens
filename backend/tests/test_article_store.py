"""
Unit tests for article storage — uses in-memory SQLite, no external services.
Run: cd backend && .venv/bin/python -m pytest tests/test_article_store.py -v
"""
import sys

sys.path.insert(0, ".")

from src.storage.article_store import (
    Article,
    insert_article,
    article_exists,
    get_unembedded_articles,
    mark_embedded,
)


def _sample_article(url: str = "https://example.com/article-1") -> Article:
    return Article(
        url=url,
        title="Sample Article",
        source="TestFeed",
        published_at="2024-06-27T00:00:00Z",
        raw_text="This is the full body of a sample article for testing purposes.",
    )


class TestInsertArticle:

    def test_insert_returns_true(self, in_memory_db):
        assert insert_article(in_memory_db, _sample_article()) is True

    def test_duplicate_url_returns_false(self, in_memory_db):
        article = _sample_article()
        insert_article(in_memory_db, article)
        assert insert_article(in_memory_db, article) is False

    def test_different_urls_both_succeed(self, in_memory_db):
        assert insert_article(in_memory_db, _sample_article("https://a.com/1")) is True
        assert insert_article(in_memory_db, _sample_article("https://a.com/2")) is True


class TestArticleExists:

    def test_exists_after_insert(self, in_memory_db):
        insert_article(in_memory_db, _sample_article())
        assert article_exists(in_memory_db, "https://example.com/article-1") is True

    def test_not_exists_before_insert(self, in_memory_db):
        assert article_exists(in_memory_db, "https://example.com/never-inserted") is False


class TestEmbeddingQueue:

    def test_new_article_appears_in_unembedded(self, in_memory_db):
        insert_article(in_memory_db, _sample_article())
        rows = get_unembedded_articles(in_memory_db)
        assert len(rows) == 1
        assert rows[0]["url"] == "https://example.com/article-1"

    def test_mark_embedded_removes_from_queue(self, in_memory_db):
        insert_article(in_memory_db, _sample_article())
        rows = get_unembedded_articles(in_memory_db)
        article_id = rows[0]["id"]

        mark_embedded(in_memory_db, article_id)

        assert get_unembedded_articles(in_memory_db) == []

    def test_mark_embedded_is_idempotent(self, in_memory_db):
        insert_article(in_memory_db, _sample_article())
        rows = get_unembedded_articles(in_memory_db)
        article_id = rows[0]["id"]

        mark_embedded(in_memory_db, article_id)
        mark_embedded(in_memory_db, article_id)  # should not raise

        assert get_unembedded_articles(in_memory_db) == []
