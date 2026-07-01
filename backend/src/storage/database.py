import sqlite3
from pathlib import Path

from src.storage.schema import create_schema

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
        create_schema(_conn)
    return _conn
