# TrendLens

A time-weighted RAG system that ingests tech news from multiple RSS sources
and answers questions like *"What's new in AI this week?"* with synthesized,
source-cited answers grounded in recent articles — not a link dump, and not
a model guessing from a stale training cutoff.

## Why This Exists

Keeping up with tech news is overwhelming. Search engines give you
individual links, chat models have a knowledge cutoff, and newsletter
aggregators organize without synthesizing. TrendLens keeps a continuously
updated knowledge base of recent articles and lets you query it
conversationally, with time-awareness built into retrieval — recent content
is prioritized, not just similar content.

## How It Works

1. **Ingestion** — RSS feeds (Ars Technica, TechCrunch, The Verge, Hacker
   News, MIT Technology Review, Wired) are polled on a schedule. Articles
   are fetched, cleaned, and deduplicated by URL into SQLite.
2. **Processing** — Articles are split into overlapping, word-bounded
   chunks and embedded with OpenAI's `text-embedding-3-small`.
3. **Storage** — Dense embeddings and BM25 sparse vectors are stored in
   Qdrant; article metadata and ingestion state live in SQLite.
4. **Retrieval** — A query is parsed for a time phrase ("this week" → last
   7 days), then run as a hybrid dense + BM25 search fused server-side
   (RRF) and reranked with a local cross-encoder for precision.
5. **Generation** — The top reranked chunks are assembled into a prompt;
   `gpt-4o-mini` synthesizes an answer with inline source citations.

## Repository Layout

```
backend/    FastAPI service — ingestion, retrieval, generation, eval harness
frontend/   React (Vite) UI — query box, answer panel, citations
docs/       Learning journal and design notes
docker-compose.yml   Qdrant (the only containerized service today)
```

Each side has its own README with setup details:
[backend/readme.md](backend/readme.md) · [frontend/README.md](frontend/README.md).
The full engineering write-up — every decision, tradeoff, and known gap —
is in [backend/Design.md](backend/Design.md).

## Quick Start

**Prerequisites:** Docker, Python 3.11+, Node 18+, an OpenAI API key.

```bash
git clone https://github.com/rmadil9/trendlens.git
cd trendlens
cp backend/.env.example backend/.env
# add your OPENAI_API_KEY to backend/.env

# vector store
docker compose up qdrant -d

# backend
cd backend
pip install -r requirements.txt
python scripts/seed_feeds.py       # initial ingestion
uvicorn src.api.main:app --reload

# frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and ask a question.

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Vector store | Qdrant (dense + BM25 sparse, RRF fusion) | Native metadata filtering plus hybrid search for named-entity precision |
| Reranking | Cross-encoder (`ms-marco-MiniLM-L-6-v2`) | Cleans up hybrid candidates before generation |
| Embedding | `text-embedding-3-small` (OpenAI) | Strong retrieval quality, isolated behind a swappable interface |
| Generation | `gpt-4o-mini` (OpenAI) | Cost-effective, sufficient for grounded synthesis |
| Backend | FastAPI (Python) | Async, auto-docs, Python-native |
| Frontend | React + Vite | Fast dev loop, interactive UI |
| Metadata store | SQLite | Article dedup and ingestion tracking |

## Status

Core pipeline (ingestion → hybrid retrieval → reranking → generation → API →
UI) is built and hand-evaluated (15 curated queries, see
[backend/readme.md](backend/readme.md#evaluation) for scores). Still open:
event-driven ingestion, scheduled digests, CI/CD, and a production Docker
build for the backend/frontend — see the Design Document for the full list.

## License

MIT
