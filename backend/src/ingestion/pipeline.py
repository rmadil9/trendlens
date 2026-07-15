import logging
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")  # must run before any module reads env vars

from src.storage.database import get_connection
from src.storage.article_store import Article, get_unembedded_articles, mark_embedded
from src.storage.vector_store import get_client, ensure_collection
from src.storage.chunk_store import upsert_chunks
from src.ingestion.chunker import chunk_article
from src.ingestion.embedder import embed_chunks
from src.ingestion.sparse_embedder import embed_chunks_sparse

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    """Embed cron (Cron 2): pulls only rows with is_embedded=0, so re-running
    this on a schedule never re-embeds articles already pushed to Qdrant."""
    conn = get_connection()
    qdrant = get_client()
    ensure_collection(qdrant)

    rows = get_unembedded_articles(conn)

    if not rows:
        logger.info("No unembedded articles — nothing to do")
        return

    logger.info("Processing %d unembedded articles", len(rows))

    total_chunks = 0
    for row in rows:
        article = Article(
            id=row["id"],
            url=row["url"],
            title=row["title"],
            source=row["source"],
            published_at=row["published_at"],
            raw_text=row["raw_text"],
        )

        try:
            chunks = chunk_article(article)
            if not chunks:
                mark_embedded(conn, article.id)  # nothing to embed — don't retry forever
                continue

            embedded = embed_chunks(chunks)
            embedded = embed_chunks_sparse(embedded)
            upsert_chunks(qdrant, embedded)
            mark_embedded(conn, article.id)
            total_chunks += len(embedded)
            logger.info("  ✓ %s — %d chunks", article.title[:60], len(embedded))
        except Exception:
            # Leave is_embedded=0 so this article is retried on the next cron run
            logger.exception("  ✗ Failed to embed %s — will retry next run", article.url)

    logger.info("Done. %d total chunks upserted into Qdrant", total_chunks)


if __name__ == "__main__":
    run()
