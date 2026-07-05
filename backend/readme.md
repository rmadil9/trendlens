# TrendLens

A time-weighted RAG system that ingests tech news from multiple sources
and lets you ask questions like *"What's new in AI this week?"* — getting
synthesized, source-cited answers grounded in recent articles.

## Why This Exists

Keeping up with tech news is overwhelming. Google gives you individual
links. ChatGPT has a knowledge cutoff. Newsletter aggregators organize
but don't synthesize. TrendLens maintains a continuously updated
knowledge base of recent articles and lets you query it conversationally,
with time-awareness built into retrieval — recent content is prioritized,
not just similar content.

## How It Works

1. **Ingestion** — RSS feeds are polled on a schedule. Articles are
   fetched, cleaned, and deduplicated.
2. **Processing** — Articles are split into chunks with metadata
   (source, date, title) and embedded using OpenAI's
   text-embedding-3-small model.
3. **Storage** — Embeddings are stored in Qdrant (vector search).
   Article metadata lives in SQLite (deduplication, tracking).
4. **Retrieval** — User queries are embedded, then matched against
   chunks filtered by time window. "This week" only searches the
   last 7 days.
5. **Generation** — Retrieved chunks are assembled into a prompt.
   GPT-4o-mini synthesizes an answer with source citations.

## Architecture

See [Design.md](Design.md) for detailed design decisions,
tradeoffs, and engineering reasoning.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key

### Run locally
```bash
git clone https://github.com/rmadil9/trendlens.git
cd trendlens
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# Start infrastructure
docker compose up qdrant -d

# Start backend
cd backend
pip install -r requirements.txt
python scripts/seed_feeds.py    # Initial ingestion
uvicorn src.api.main:app --reload

# Start frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and ask a question.

### Run with Docker (production-like)
> **Not wired up yet.** `docker-compose.yml` currently only defines the
> Qdrant service — there's no backend/frontend Dockerfile and no
> `production` profile. This command is aspirational until that's built.
```bash
docker compose --profile production up --build
```

## Evaluation

I tested the system against 15 curated queries across 5 categories
(basic retrieval, time-weighting, specificity, edge cases, answer
quality). Results:

| Metric | Score |
|---|---|
| Retrieval Precision@5 (excl. edge cases) | 82% |
| Retrieval Precision@5 (all 15) | 68% |
| Time-filter Accuracy | 80% (12/15) |
| Answer Faithfulness | 87% (13/15) |
| Citation Accuracy | ~87% |

3 of the 15 queries are deliberately adversarial (off-topic / a known
time-parsing gap) and are *expected* to score low — see
[Design.md](Design.md#6-evaluation) for the breakdown and the one bug
found and fixed during this eval pass (a prompt-instruction gap that made
the refusal guardrail fire even after the model had already answered part
of a multi-part question).

See [eval/test_queries.md](eval/test_queries.md) for the
full test set and [eval/results/](eval/results/) for
detailed scoring.

## Tech Stack

| Component | Choice | Why |
|---|---|---|
| Embedding | text-embedding-3-small (OpenAI) | Higher retrieval quality, parameterized for swap to local model |
| Vector Store | Qdrant | Native metadata filtering for time-weighted retrieval |
| Generation | GPT-4o-mini (OpenAI) | Cost-effective, strong instruction following |
| Backend | FastAPI (Python) | Async, auto-docs, Python-native |
| Frontend | React | Polished interactive UI |
| Message Broker | RabbitMQ (post-MVP) | Reliable delivery with dead-letter support |
| Database | SQLite | Article deduplication and ingestion tracking |

## Project Status

- [x] Project planning and design
- [x] Ingestion pipeline (RSS → clean text → chunks)
- [x] Embedding + Qdrant storage
- [x] Retrieval with time-weighting
- [x] Generation with citations
- [x] API endpoints
- [x] Web UI
- [x] Evaluation (hand-scored, 15 queries — see above)
- [ ] Event-driven ingestion (RabbitMQ) — still cron-based
- [ ] Scheduled digests
- [ ] UI polish
- [ ] CI/CD (GitHub Actions)
- [ ] Production Docker build (only Qdrant is containerized today)
- [ ] Demo GIF / architecture diagram

## Design Document

The full engineering thinking behind this project — every decision,
tradeoff, and deliberate omission — is documented in
[Design.md](Design.md).

## License

MIT

