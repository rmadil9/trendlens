import sqlite3

# Dedup relies solely on the UNIQUE constraint on url — no content hash column.
CREATE_ARTICLES_TABLE = """
    CREATE TABLE IF NOT EXISTS articles (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        url           TEXT    NOT NULL UNIQUE,   -- dedup anchor
        title         TEXT,
        source        TEXT,                       -- feed name, e.g. "TechCrunch"
        published_at  TEXT,                       -- ISO-8601 string; TEXT because SQLite has no native datetime
        raw_text      TEXT,                       -- cleaned article body
        ingested_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
    )
"""

# Speeds up the time-range queries we'll run during retrieval
CREATE_PUBLISHED_AT_INDEX = "CREATE INDEX IF NOT EXISTS idx_published_at ON articles(published_at)"
CREATE_SOURCE_INDEX = "CREATE INDEX IF NOT EXISTS idx_source ON articles(source)"


def create_schema(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_ARTICLES_TABLE)
    conn.execute(CREATE_PUBLISHED_AT_INDEX)
    conn.execute(CREATE_SOURCE_INDEX)
    conn.commit()
