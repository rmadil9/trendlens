import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime  # parses RFC-2822 dates from RSS

import feedparser
import httpx

from src.ingestion.cleaner import html_to_text, is_too_short
from src.ingestion.feeds import Feed
from src.storage.article_store import Article

logger = logging.getLogger(__name__)

# Mimic a browser — some outlets block Python's default user-agent
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TrendLens/1.0)"}
FETCH_TIMEOUT = 15  # seconds per article request


def poll_feed(feed: Feed, max_articles: int = 20) -> list[Article]:
    """Parse one RSS feed and return cleaned Article objects ready for storage."""
    parsed = feedparser.parse(feed.url)

    if parsed.bozo:
        # feedparser sets bozo=True when the feed is malformed — log and continue
        logger.warning("Malformed feed %s: %s", feed.name, parsed.bozo_exception)

    articles = []
    for entry in parsed.entries[:max_articles]:
        article = _process_entry(entry, feed.name)
        if article:
            articles.append(article)

    logger.info("Feed %s: %d/%d articles fetched", feed.name, len(articles), len(parsed.entries[:max_articles]))
    return articles


def _process_entry(entry, source: str) -> Article | None:
    url = entry.get("link", "").strip()
    title = entry.get("title", "").strip()

    if not url:
        return None

    published_at = _parse_date(entry)

    # Try to get full text from the feed itself first (some feeds include it)
    inline_text = _extract_inline_text(entry)

    if inline_text and not is_too_short(inline_text):
        raw_text = inline_text
    else:
        # Fallback: fetch the article page and clean it
        raw_text = _fetch_and_clean(url)

    if not raw_text or is_too_short(raw_text):
        logger.debug("Skipping short/empty article: %s", url)
        return None

    return Article(
        url=url,
        title=title,
        source=source,
        published_at=published_at,
        raw_text=raw_text,
    )


def _extract_inline_text(entry) -> str:
    """Some RSS feeds include full article HTML in the `content` or `summary` field."""
    if entry.get("content"):
        return html_to_text(entry["content"][0].get("value", ""))
    if entry.get("summary"):
        return html_to_text(entry["summary"])
    return ""


def _fetch_and_clean(url: str) -> str:
    try:
        response = httpx.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT,
                             follow_redirects=True)
        response.raise_for_status()
        return html_to_text(response.text)
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return ""


def _parse_date(entry) -> str:
    """Return ISO-8601 UTC string. Falls back to now() if feed date is missing/broken."""
    for field in ("published", "updated"):
        raw = entry.get(field)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
