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

Open http://localhost:5173 and ask a question.

### Run the production stack
Four containers — nginx (TLS + static + `/api` proxy), backend, qdrant,
certbot. Only nginx publishes ports.
```bash
cp .env.example .env                    # DOMAIN, CERTBOT_EMAIL
cp backend/.env.example backend/.env    # OPENAI_API_KEY
docker compose -f docker-compose.prod.yml up -d --build
```
Certificate bootstrap and crontab install are in the
[root README](../README.md#deployment). Full architecture and rationale in
[Design.md](Design.md#9-deployment).

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
| Vector Store | Qdrant (dense + BM25 sparse, RRF fusion) | Native metadata filtering plus hybrid search for named-entity precision |
| Reranking | Cross-encoder (`ms-marco-MiniLM-L-6-v2`, local) | Cleans up fused candidates before generation |
| Generation | GPT-4o-mini (OpenAI) | Cost-effective, strong instruction following |
| Backend | FastAPI (Python) | Async, auto-docs, Python-native |
| Frontend | React + Vite | Polished interactive UI |
| Web tier | nginx | TLS, static serving, `/api` proxy, edge rate limiting |
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
- [x] Hybrid retrieval (dense + BM25, RRF) with cross-encoder reranking
- [x] CI (GitHub Actions — backend tests, frontend lint + build)
- [x] Production Docker build — 4-container stack, live at
      [trendlens.adil9.tech](https://trendlens.adil9.tech)
- [ ] Event-driven ingestion (RabbitMQ) — still cron-based
- [ ] Scheduled digests
- [ ] UI polish
- [ ] Deploy-on-merge (deployment is still a manual `git pull` on the VPS)
- [ ] Backups for the Qdrant volume and SQLite DB
- [ ] Cost caps / budget alerts on the public API
- [ ] Demo GIF / architecture diagram

## Design Document

The full engineering thinking behind this project — every decision,
tradeoff, and deliberate omission — is documented in
[Design.md](Design.md).

## License

MIT

