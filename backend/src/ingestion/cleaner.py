import re
from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Remove tags that are never article content
    for tag in soup(["script", "style", "nav", "header", "footer",
                      "aside", "form", "noscript", "iframe"]):
        tag.decompose()  # removes the tag AND its children from the tree

    text = soup.get_text(separator="\n")

    # Collapse runs of blank lines into a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def is_too_short(text: str, min_chars: int = 200) -> bool:
    """Reject paywalled or stub articles that slipped through."""
    return len(text.strip()) < min_chars
