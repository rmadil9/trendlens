from datetime import datetime, timezone

NO_RELEVANT_INFO_MESSAGE = (
    "Sorry, I could not find relevant information in the latest news articles "
    "to answer your question."
)


def build_prompt(chunks: list[dict], question: str) -> tuple[str, str]:
    """
    Build (system_prompt, user_prompt) from retrieved chunks and the question.

    Returns a tuple so the caller can pass them to the chat API separately:
      - system_prompt goes into the 'system' role message
      - user_prompt goes into the 'user' role message

    Why split instead of one big string?
    Chat models (GPT-4o-mini) treat 'system' and 'user' differently.
    System = persistent instructions the model treats as authoritative.
    User = the turn it's responding to. Mixing them into one string weakens both.
    """
    system_prompt = (
        "You are a news analyst assistant for TrendLens. "
        "Your job is to answer questions using ONLY the news articles provided below. "
        "Do not use any knowledge from your training data. "
        "If the question has multiple parts and the articles only support some of them, "
        "answer the parts you can support and simply omit the rest — do not add a refusal "
        "statement just because one part of the question goes unanswered. "
        "Only if NONE of the provided articles are relevant to the question, say exactly: "
        f"\"{NO_RELEVANT_INFO_MESSAGE}\" and say nothing else."
    )

    context_block = _format_chunks(chunks)

    user_prompt = (
        f"Here are the relevant news articles retrieved for your question:\n\n"
        f"{context_block}\n"
        f"---\n\n"
        f"Question: {question}\n\n"
        f"Instructions:\n"
        f"- Answer using only the articles chunks above.\n"
        f"- After each claim, cite the source like this: [TechCrunch, 2026-06-25]\n"
        f"- If multiple articles support a claim, cite all of them.\n"
        f"- If NONE of the articles are relevant, say \"{NO_RELEVANT_INFO_MESSAGE}\" and nothing else. "
        f"If only SOME parts of the question are supported, answer those parts and leave out the rest — do not add the refusal sentence in that case.\n"
        f"- Do not invent facts, URLs, or quotes not present in the articles above."
        f"- Answer in bullets poins not more than 3-5 or answer in short paragraphs if needed with 3-5 lines in each paragraph and maximum number of paragrah should not be more than 2"
        f"- Bold the important terms or entities in the answer for sake of highlighting"
    )

    return system_prompt, user_prompt


def _format_chunks(chunks: list[dict]) -> str:
    """
    Render each chunk as a tagged block the model can read and cite from.

    Format per chunk:
        [Source: TechCrunch | Date: 2026-06-25 | URL: https://...]
        <the actual text of the chunk>

    Why include the URL?
    The model can echo it in citations so the user can click through.
    We instruct it to cite [Source, Date] — the URL is there if it needs it.
    """
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        date_str = unix_to_date(chunk["published_at"])
        header = f"[Article {i} | Source: {chunk['source']} | Date: {date_str} | URL: {chunk['url']}]"
        blocks.append(f"{header}\n{chunk['text']}")

    return "\n\n".join(blocks)


def unix_to_date(ts: int) -> str:
    """Convert Unix timestamp → human-readable date string for the prompt."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
