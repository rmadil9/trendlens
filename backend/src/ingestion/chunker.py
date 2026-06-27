from datetime import datetime, timezone

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.storage.article_store import Article

# ~500 words ≈ ~650 tokens for news prose; overlap keeps boundary sentences coherent
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,          # measured in characters by default — we override below
    chunk_overlap=50,
    length_function=lambda text: len(text.split()),   # count words, not chars
    separators=["\n\n", "\n", ". ", " ", ""],         # paragraph → line → sentence → word → char
)


def chunk_article(article: Article) -> list[dict]:
    """Split article text into overlapping chunks, each carrying its own metadata."""
    texts = _splitter.split_text(article.raw_text)

    # Convert published_at ISO string → Unix timestamp integer for Qdrant range filters
    published_ts = _iso_to_unix(article.published_at)

    chunks = []
    for i, text in enumerate(texts):
        chunks.append({
            "text": text,
            "source": article.source,
            "title": article.title,
            "url": article.url,
            "published_at": published_ts,   # numeric — required for tomorrow's time filter
            "chunk_index": i,
        })

    return chunks


def _iso_to_unix(iso: str) -> int:
    """Parse ISO-8601 UTC string (e.g. '2024-06-27T00:00:00Z') → Unix timestamp."""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return int(dt.timestamp())
