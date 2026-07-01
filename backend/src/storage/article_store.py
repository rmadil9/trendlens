import sqlite3
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Article:
    url: str
    title: str
    source: str
    published_at: str   # ISO-8601
    raw_text: str
    id: int = 0
    ingested_at: str = ""


def insert_article(conn: sqlite3.Connection, article: Article) -> bool:
    """Insert article. Returns True if inserted, False if duplicate (silently skipped)."""
    try:
        conn.execute(
            """
            INSERT INTO articles (url, title, source, published_at, raw_text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (article.url, article.title, article.source,
             article.published_at, article.raw_text),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # UNIQUE constraint on url fired — this is expected for dupes
        return False


def article_exists(conn: sqlite3.Connection, url: str) -> bool:
    """Check if article already stored by URL."""
    row = conn.execute(
        "SELECT 1 FROM articles WHERE url = ? LIMIT 1",
        (url,),
    ).fetchone()
    return row is not None


def get_articles_since(conn: sqlite3.Connection, since: datetime) -> list[sqlite3.Row]:
    """Fetch articles published after `since`. Used by the retrieval layer."""
    return conn.execute(
        "SELECT * FROM articles WHERE published_at >= ? ORDER BY published_at DESC",
        (since.isoformat(),),
    ).fetchall()


def get_unembedded_articles(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Fetch articles not yet embedded into Qdrant — the embed cron's work queue."""
    return conn.execute(
        "SELECT id, url, title, source, published_at, raw_text "
        "FROM articles WHERE is_embedded = 0"
    ).fetchall()


def mark_embedded(conn: sqlite3.Connection, article_id: int) -> None:
    """Flip is_embedded to 1 after a successful Qdrant upsert.

    Commits immediately (per-article, not batched) so a crash partway through
    a run leaves already-embedded articles marked done — only the remainder
    gets retried on the next cron run.
    """
    conn.execute("UPDATE articles SET is_embedded = 1 WHERE id = ?", (article_id,))
    conn.commit()
