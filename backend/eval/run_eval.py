"""
Eval runner — executes all 15 test queries against the live retrieval +
generation pipeline and dumps raw output (retrieved chunks, generated
answer, source list) to a timestamped markdown file for manual scoring.

This script does NOT score anything. Precision@5, time-filter
correctness, faithfulness, and citation accuracy all require human
judgment against the dumped evidence — see eval/SCORING.md for the rubric.

Cost: 15 queries = 15 embedding calls + 15 chat completion calls.

Usage (from backend/):
    .venv/bin/python -m eval.run_eval
"""
import logging
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")  # must run before any module reads OPENAI_API_KEY

from src.storage.vector_store import get_client, ensure_collection
from src.retrieval.retriever import retrieve
from src.generation.generator import generate_answer
from src.retrieval.sources import dedupe_sources
from src.generation.prompt import unix_to_date
from eval.queries import QUERIES

# WARNING not INFO — the eval output file is the thing to read, not the
# console; this keeps httpx/qdrant request logs out of the way.
logging.basicConfig(level=logging.WARNING)

RESULTS_DIR = Path(__file__).parent / "results"


def run() -> Path:
    qdrant = get_client()
    ensure_collection(qdrant)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    # Timestamped filename — each eval run is kept, not overwritten, so you
    # can compare a "before" and "after" run once you make a change.
    out_path = RESULTS_DIR / f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.md"

    lines = [f"# Eval run — {datetime.now(timezone.utc).isoformat()}\n"]

    for q in QUERIES:
        print(f"[{q['id']:2d}] {q['category']}: {q['question']}")

        chunks = retrieve(q["question"], qdrant)
        answer = generate_answer(q["question"], chunks)
        sources = dedupe_sources(chunks)

        lines.append(f"## {q['id']}. [{q['category']}] {q['question']}\n")
        if q.get("note"):
            lines.append(f"> **Expected:** {q['note']}\n")

        lines.append(f"**Retrieved chunks ({len(chunks)}):**\n")
        if not chunks:
            lines.append("_None retrieved._\n")
        else:
            for i, c in enumerate(chunks, start=1):
                # First 180 chars of the chunk text, newlines flattened —
                # enough to judge relevance without dumping the full article.
                preview = c["text"][:180].replace("\n", " ")
                lines.append(
                    f"{i}. score={c['score']:.3f} | {c['source']} | "
                    f"{unix_to_date(c['published_at'])} | {c['title']}\n"
                    f"   > {preview}...\n"
                )

        lines.append(f"\n**Answer:**\n\n{answer}\n")

        lines.append(f"\n**Deduped sources ({len(sources)}):**\n")
        if not sources:
            lines.append("_None._\n")
        for s in sources:
            lines.append(f"- {s['source']} — {s['title']} ({unix_to_date(s['published_at'])})\n")

        lines.append("\n---\n")

    out_path.write_text("\n".join(lines))
    print(f"\nWrote {out_path}")
    return out_path


if __name__ == "__main__":
    run()
