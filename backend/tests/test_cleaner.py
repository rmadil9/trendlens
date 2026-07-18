"""
Unit tests for the HTML cleaner — deterministic, no external services.
Run: cd backend && .venv/bin/python -m pytest tests/test_cleaner.py -v
"""
import sys

sys.path.insert(0, ".")

from src.ingestion.cleaner import html_to_text, is_too_short


class TestHtmlToText:

    def test_strips_script_and_style_tags(self):
        html = (
            "<html><body>"
            "<script>alert('xss')</script>"
            "<style>.cls { color: red; }</style>"
            "<p>Visible content</p>"
            "</body></html>"
        )
        result = html_to_text(html)
        assert "alert" not in result
        assert "color" not in result
        assert "Visible content" in result

    def test_preserves_paragraph_text(self):
        html = "<p>First paragraph.</p><p>Second paragraph.</p>"
        result = html_to_text(html)
        assert "First paragraph." in result
        assert "Second paragraph." in result

    def test_removes_nav_header_footer(self):
        html = (
            "<nav>Menu links</nav>"
            "<header>Site header</header>"
            "<article><p>Article body</p></article>"
            "<footer>Copyright 2024</footer>"
        )
        result = html_to_text(html)
        assert "Menu links" not in result
        assert "Site header" not in result
        assert "Copyright 2024" not in result
        assert "Article body" in result

    def test_collapses_blank_lines(self):
        html = "<p>Line one</p>" + "<br/>" * 10 + "<p>Line two</p>"
        result = html_to_text(html)
        # Should never have more than one blank line (2 consecutive newlines)
        assert "\n\n\n" not in result

    def test_empty_html_returns_empty(self):
        assert html_to_text("") == ""

    def test_plain_text_passthrough(self):
        text = "Just a plain string with no HTML."
        assert html_to_text(text) == text


class TestIsTooShort:

    def test_rejects_stub_article(self):
        stub = "This is a paywall stub."
        assert is_too_short(stub) is True

    def test_passes_real_article(self):
        real = "A" * 500
        assert is_too_short(real) is False

    def test_respects_custom_threshold(self):
        text = "A" * 50
        assert is_too_short(text, min_chars=100) is True
        assert is_too_short(text, min_chars=30) is False

    def test_whitespace_only_is_too_short(self):
        assert is_too_short("   \n\n\t  ") is True
