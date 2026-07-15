import logging
from datetime import datetime, timezone

from openai import (
    OpenAI,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
)
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.generation.prompt import build_prompt
from src.retrieval.sources import dedupe_sources

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"
TEMPERATURE = 0.2   # low = more faithful to context, less creative invention
MAX_TOKENS = 1024

# Retry only on transient failures (timeouts, connection drops, 5xx) — not
# RateLimitError, since rate-limit windows (per-minute quotas) reset on a
# timescale far longer than our max ~10s backoff would cover, and not 4xx
# like bad requests or auth errors, which won't succeed on retry either.
_RETRYABLE = (APITimeoutError, APIConnectionError, InternalServerError)


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


@retry(
    retry=retry_if_exception_type(_RETRYABLE),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _call_chat_completion(client: OpenAI, system_prompt: str, user_prompt: str):
    return client.chat.completions.create(
        model=MODEL,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
    )


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
    response = _call_chat_completion(client, system_prompt, user_prompt)

    answer = response.choices[0].message.content.strip()

    logger.info(
        "Generated answer (%d tokens used — prompt: %d, completion: %d)",
        response.usage.total_tokens,
        response.usage.prompt_tokens,
        response.usage.completion_tokens,
    )

    return answer


def _assemble_sources(chunks: list[dict]) -> str:
    """
    Render the canonical source list (see dedupe_sources) as printable text
    for the CLI. The API renders the same list as JSON Source objects
    instead (src/api/routes/query.py) — both read from dedupe_sources so
    they can't disagree on which articles were cited.

    Why build from chunks and not from the model's output?
    Parsing the model's cited sources is fragile — it might paraphrase
    a source name or drop one. The chunks are ground truth: if a chunk
    was retrieved, its source is real. We list all retrieved sources and
    let the model's inline citations connect claims to them.
    """
    lines = ["**Sources:**"]

    for i, s in enumerate(dedupe_sources(chunks), start=1):
        date_str = datetime.fromtimestamp(s["published_at"], tz=timezone.utc).strftime("%Y-%m-%d")
        lines.append(f"[{i}] {s['source']} — {s['title']} ({date_str})\n    {s['url']}")

    return "\n".join(lines)
