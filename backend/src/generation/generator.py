import logging
from openai import OpenAI

from src.generation.prompt import build_prompt

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"
TEMPERATURE = 0.2   # low = more faithful to context, less creative invention
MAX_TOKENS = 1024


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def generate_answer(question: str, chunks: list[dict]) -> str:
    """
    Given a question and retrieved chunks, call GPT-4o-mini and return
    a cited answer with a sources list appended at the bottom.

    Returns a plain string ready to print or send to the frontend.
    Returns a fallback message if no chunks were retrieved.
    """
    if not chunks:
        return (
            "I don't know based on the available articles. "
            "No articles were found in the selected time window. "
            "Try broadening your query or removing a time constraint."
        )

    system_prompt, user_prompt = build_prompt(chunks, question)

    client = _get_client()
    response = client.chat.completions.create(
        model=MODEL,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )

    answer = response.choices[0].message.content.strip()
    sources_block = _assemble_sources(chunks)

    logger.info(
        "Generated answer (%d tokens used — prompt: %d, completion: %d)",
        response.usage.total_tokens,
        response.usage.prompt_tokens,
        response.usage.completion_tokens,
    )

    return f"{answer}\n\n{sources_block}"


def _assemble_sources(chunks: list[dict]) -> str:
    """
    Build a deduplicated sources list from the retrieved chunks.

    Why build from chunks and not from the model's output?
    Parsing the model's cited sources is fragile — it might paraphrase
    a source name or drop one. The chunks are ground truth: if a chunk
    was retrieved, its source is real. We list all retrieved sources and
    let the model's inline citations connect claims to them.
    """
    seen_urls = set()
    lines = ["**Sources:**"]

    for i, chunk in enumerate(chunks, start=1):
        url = chunk["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)

        from datetime import datetime, timezone
        date_str = datetime.fromtimestamp(chunk["published_at"], tz=timezone.utc).strftime("%Y-%m-%d")
        lines.append(f"[{i}] {chunk['source']} — {chunk['title']} ({date_str})\n    {url}")

    return "\n".join(lines)
