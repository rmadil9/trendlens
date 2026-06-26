import sqlite3
from pathlib import Path

# Single connection per process — SQLite doesn't support concurrent writes,
# so we keep one connection and use check_same_thread=False for FastAPI.
_conn: sqlite3.Connection | None = None


def get_connection(db_path: str = "./data/trendlens.db") -> sqlite3.Connection:
    global _conn
    if _conn is None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(db_path, check_same_thread=False)
        # Row factory makes rows behave like dicts: row["title"] instead of row[1]
        _conn.row_factory = sqlite3.Row
        _create_schema(_conn)
    return _conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            url           TEXT    NOT NULL UNIQUE,   -- dedup anchor #1
            title         TEXT,
            source        TEXT,                       -- feed name, e.g. "TechCrunch"
            published_at  TEXT,                       -- ISO-8601 string; TEXT because SQLite has no native datetime
            raw_text      TEXT,                       -- cleaned article body
            ingested_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    # Speeds up the time-range queries we'll run during retrieval
    conn.execute("CREATE INDEX IF NOT EXISTS idx_published_at ON articles(published_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON articles(source)")
    conn.commit()
