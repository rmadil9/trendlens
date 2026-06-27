import logging
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")  # must run before any module reads env vars

from src.storage.database import get_connection
from src.storage.article_store import Article
from src.storage.vector_store import get_client, ensure_collection, upsert_chunks
from src.ingestion.chunker import chunk_article
from src.ingestion.embedder import embed_chunks

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    conn = get_connection()
    qdrant = get_client()
    ensure_collection(qdrant)

    rows = conn.execute(
        "SELECT url, title, source, published_at, raw_text FROM articles"
    ).fetchall()

    if not rows:
        logger.info("No articles in SQLite — run the fetcher first")
        return

    logger.info("Processing %d articles", len(rows))

    total_chunks = 0
    for row in rows:
        article = Article(
            url=row["url"],
            title=row["title"],
            source=row["source"],
            published_at=row["published_at"],
            raw_text=row["raw_text"],
        )

        chunks = chunk_article(article)
        if not chunks:
            continue

        embedded = embed_chunks(chunks)
        upsert_chunks(qdrant, embedded)
        total_chunks += len(embedded)
        logger.info("  ✓ %s — %d chunks", article.title[:60], len(embedded))

    logger.info("Done. %d total chunks upserted into Qdrant", total_chunks)


if __name__ == "__main__":
    run()
