"""
Usage:
    cd backend
    .venv/bin/python scripts/ask.py "what's new in AI this week?"
"""
import sys
import logging
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")  # must run before any module reads OPENAI_API_KEY

from src.storage.vector_store import get_client, ensure_collection
from src.retrieval.retriever import retrieve
from src.generation.generator import generate_answer, _assemble_sources

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/ask.py \"your question here\"")
        sys.exit(1)

    question = sys.argv[1]
    print(f"\nQuestion: {question}\n{'─' * 60}")

    qdrant = get_client()
    ensure_collection(qdrant)

    chunks = retrieve(question, qdrant)

    if not chunks:
        print("No recent articles found for this query.")
        print("Tip: run the ingestion pipeline first (python src/ingestion/pipeline.py)")
        sys.exit(0)

    print(f"Retrieved {len(chunks)} chunks (top score: {chunks[0]['score']:.3f})\n")

    answer = generate_answer(question, chunks)
    print(answer)
    print()
    print(_assemble_sources(chunks))


if __name__ == "__main__":
    main()
