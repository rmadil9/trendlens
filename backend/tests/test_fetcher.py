"""
Unit tests for the fetcher's internal parsing logic — deterministic, no network.
Run: cd backend && .venv/bin/python -m pytest tests/test_fetcher.py -v

We test _parse_date, _extract_inline_text, and _process_entry directly.
HTTP calls (_fetch_and_clean) are mocked so tests never hit the network.
"""
import sys
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, ".")

from src.ingestion.fetcher import _parse_date, _extract_inline_text, _process_entry


# ── _parse_date ───────────────────────────────────────────────────────────────

class TestParseDate:

    def test_rfc2822_date_parsed_correctly(self):
        entry = {"published": "Thu, 27 Jun 2024 00:00:00 +0000"}
        result = _parse_date(entry)
        assert result == "2024-06-27T00:00:00Z"

    def test_uses_updated_field_as_fallback(self):
        entry = {"updated": "Thu, 27 Jun 2024 12:30:00 +0000"}
        result = _parse_date(entry)
        assert result == "2024-06-27T12:30:00Z"

    def test_missing_date_falls_back_to_now(self):
        entry = {}  # no published or updated
        result = _parse_date(entry)
        # Should be today's date (ISO-8601 UTC)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert result.startswith(today)

    def test_malformed_date_falls_back_to_now(self):
        entry = {"published": "not-a-real-date"}
        result = _parse_date(entry)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert result.startswith(today)


# ── _extract_inline_text ─────────────────────────────────────────────────────

class TestExtractInlineText:

    def test_extracts_from_content_field(self):
        entry = {"content": [{"value": "<p>Full article body here.</p>"}]}
        result = _extract_inline_text(entry)
        assert "Full article body here." in result

    def test_extracts_from_summary_field(self):
        entry = {"summary": "<p>Summary text.</p>"}
        result = _extract_inline_text(entry)
        assert "Summary text." in result

    def test_content_takes_priority_over_summary(self):
        entry = {
            "content": [{"value": "<p>Content wins.</p>"}],
            "summary": "<p>Summary loses.</p>",
        }
        result = _extract_inline_text(entry)
        assert "Content wins." in result

    def test_empty_entry_returns_empty(self):
        assert _extract_inline_text({}) == ""


# ── _process_entry ────────────────────────────────────────────────────────────

class TestProcessEntry:

    def test_skips_entry_with_no_url(self):
        entry = {"title": "No Link Article"}
        assert _process_entry(entry, "TestFeed") is None

    def test_skips_entry_with_empty_url(self):
        entry = {"link": "   ", "title": "Blank Link"}
        assert _process_entry(entry, "TestFeed") is None

    def test_returns_article_when_inline_text_sufficient(self):
        """When the RSS entry contains enough inline text, no HTTP fetch needed."""
        long_body = "This is a real article with substance. " * 20  # >200 chars
        entry = {
            "link": "https://example.com/good-article",
            "title": "Good Article",
            "published": "Thu, 27 Jun 2024 00:00:00 +0000",
            "summary": f"<p>{long_body}</p>",
        }
        article = _process_entry(entry, "TestFeed")
        assert article is not None
        assert article.url == "https://example.com/good-article"
        assert article.title == "Good Article"
        assert article.source == "TestFeed"

    @patch("src.ingestion.fetcher._fetch_and_clean", return_value="")
    def test_skips_when_fetched_text_too_short(self, mock_fetch):
        """Inline text absent + HTTP fetch returns empty → skip."""
        entry = {
            "link": "https://example.com/paywalled",
            "title": "Paywalled",
            "published": "Thu, 27 Jun 2024 00:00:00 +0000",
        }
        assert _process_entry(entry, "TestFeed") is None
        mock_fetch.assert_called_once()

    @patch("src.ingestion.fetcher._fetch_and_clean")
    def test_falls_back_to_fetch_when_inline_too_short(self, mock_fetch):
        """Inline text is a stub → falls back to HTTP fetch."""
        fetched_body = "This is a properly fetched article body. " * 20
        mock_fetch.return_value = fetched_body

        entry = {
            "link": "https://example.com/stub-inline",
            "title": "Stub Inline",
            "summary": "<p>Short.</p>",  # too short (< 200 chars)
        }
        article = _process_entry(entry, "TestFeed")
        assert article is not None
        assert fetched_body in article.raw_text
        mock_fetch.assert_called_once_with("https://example.com/stub-inline")
