import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Article:
    url: str
    title: str
    source: str
    published_at: str   # ISO-8601
    raw_text: str
    content_hash: str = ""
    id: int = 0
    ingested_at: str = ""

    def __post_init__(self):
        # Auto-compute hash if not provided — callers rarely set this manually
        if not self.content_hash:
            self.content_hash = _hash(self.raw_text)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def insert_article(conn: sqlite3.Connection, article: Article) -> bool:
    """Insert article. Returns True if inserted, False if duplicate (silently skipped)."""
    try:
        conn.execute(
            """
            INSERT INTO articles (url, title, source, published_at, raw_text, content_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (article.url, article.title, article.source,
             article.published_at, article.raw_text, article.content_hash),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # UNIQUE constraint on url or content_hash fired — this is expected for dupes
        return False


def article_exists(conn: sqlite3.Connection, url: str, content_hash: str) -> bool:
    """Check by EITHER url or hash — catches reposts and URL redirects."""
    row = conn.execute(
        "SELECT 1 FROM articles WHERE url = ? OR content_hash = ? LIMIT 1",
        (url, content_hash),
    ).fetchone()
    return row is not None


def get_articles_since(conn: sqlite3.Connection, since: datetime) -> list[sqlite3.Row]:
    """Fetch articles published after `since`. Used by the retrieval layer."""
    return conn.execute(
        "SELECT * FROM articles WHERE published_at >= ? ORDER BY published_at DESC",
        (since.isoformat(),),
    ).fetchall()
