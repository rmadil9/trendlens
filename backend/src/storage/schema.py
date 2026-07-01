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
        is_embedded   INTEGER NOT NULL DEFAULT 0,  -- 0/1 flag; doubles as the embed cron's work queue
        ingested_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
    )
"""

# Speeds up the time-range queries we'll run during retrieval
CREATE_PUBLISHED_AT_INDEX = "CREATE INDEX IF NOT EXISTS idx_published_at ON articles(published_at)"
CREATE_SOURCE_INDEX = "CREATE INDEX IF NOT EXISTS idx_source ON articles(source)"
# Speeds up "WHERE is_embedded = 0" — the embed cron's queue-polling query
CREATE_IS_EMBEDDED_INDEX = "CREATE INDEX IF NOT EXISTS idx_is_embedded ON articles(is_embedded)"


def create_schema(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_ARTICLES_TABLE)
    _migrate_add_is_embedded(conn)
    conn.execute(CREATE_PUBLISHED_AT_INDEX)
    conn.execute(CREATE_SOURCE_INDEX)
    conn.execute(CREATE_IS_EMBEDDED_INDEX)
    conn.commit()


def _migrate_add_is_embedded(conn: sqlite3.Connection) -> None:
    """Backfill is_embedded on databases created before this column existed.

    Defaults existing rows to 0 (not embedded) rather than guessing they were
    already processed — re-embedding a previously-processed article once is a
    cheap, idempotent no-op in Qdrant (deterministic point IDs), whereas
    wrongly marking one as embedded would silently drop it from the index.
    """
    columns = {row[1] for row in conn.execute("PRAGMA table_info(articles)")}
    if "is_embedded" not in columns:
        conn.execute("ALTER TABLE articles ADD COLUMN is_embedded INTEGER NOT NULL DEFAULT 0")
