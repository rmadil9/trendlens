"""
Day 1 demo script — run this to verify the ingestion pipeline works end-to-end.
Run it twice: second run should show 0 inserted (all duplicates skipped).

Usage (from backend/):
    python -m scripts.seed_feeds
"""
import logging
import sys
from pathlib import Path

# Make `src` importable when running from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.feeds import FEEDS
from src.ingestion.fetcher import poll_feed
from src.storage.article_store import insert_article
from src.storage.database import get_connection

logging.basicConfig(
    level=logging.DEBUG,                          # DEBUG so the sample entry log shows up
    format="%(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("seed_feeds")


def main():
    conn = get_connection()
    total_inserted = 0
    total_skipped = 0

    for feed in FEEDS:
        logger.info("Polling: %s", feed.name)
        articles = poll_feed(feed, max_articles=5)  # 5 per feed keeps the demo fast

        inserted = 0
        skipped = 0
        for article in articles:
            if insert_article(conn, article):  # returns False on duplicate (IntegrityError)
                inserted += 1
            else:
                skipped += 1

        logger.info("%s → inserted: %d, skipped: %d", feed.name, inserted, skipped)
        total_inserted += inserted
        total_skipped += skipped

    logger.info("=" * 50)
    logger.info("TOTAL — inserted: %d, skipped: %d", total_inserted, total_skipped)

    # Quick sanity check: query the DB and print 3 rows so you can see real data
    rows = conn.execute(
        "SELECT source, title, published_at FROM articles ORDER BY ingested_at DESC LIMIT 3"
    ).fetchall()

    logger.info("Latest 3 rows in DB:")
    for row in rows:
        logger.info("  [%s] %s (%s)", row["source"], row["title"], row["published_at"])


if __name__ == "__main__":
    main()
