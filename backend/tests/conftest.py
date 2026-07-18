"""
Shared fixtures and pytest configuration for the TrendLens test suite.

Markers:
    integration — tests that require live services (Qdrant, OpenAI API).
                  Skip with:  pytest -m "not integration"
                  Run alone:  pytest -m "integration"
"""
import sqlite3

import pytest

from src.storage.article_store import Article
from src.storage.schema import create_schema


# ── custom markers ────────────────────────────────────────────────────────────

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that need live services (Qdrant, OpenAI)",
    )


# ── factories ─────────────────────────────────────────────────────────────────

def make_article(raw_text: str = "Default article body. " * 20, **overrides) -> Article:
    """Convenience factory — supply only the fields you care about."""
    defaults = dict(
        url="https://example.com/test-article",
        title="Test Article",
        source="TestFeed",
        published_at="2024-06-27T00:00:00Z",
        raw_text=raw_text,
    )
    defaults.update(overrides)
    return Article(**defaults)


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def in_memory_db():
    """Yield a fresh in-memory SQLite connection with the schema applied.

    Tears down automatically — no cleanup needed.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    yield conn
    conn.close()
