def dedupe_sources(chunks: list[dict]) -> list[dict]:
    """
    Collapse retrieved chunks down to one record per article, deduped by URL.

    Single source of truth for "what counts as a source" — both the API
    response and the CLI's printed source list are built from this, so they
    can never disagree on which articles were cited or in what order.

    Returns raw fields (published_at stays a Unix int) — callers decide how
    to render it (JSON field vs. formatted date string).
    """
    seen_urls: set[str] = set()
    sources: list[dict] = []

    for chunk in chunks:
        url = chunk["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        sources.append({
            "title": chunk["title"],
            "url": url,
            "source": chunk["source"],
            "published_at": chunk["published_at"],
        })

    return sources
