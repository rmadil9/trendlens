# TrendLens

**Live: [trendlens.adil9.tech](https://trendlens.adil9.tech)**

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
nginx/      Production web tier — TLS, static serving, /api proxy, rate limiting
deploy/     Production cron scripts and crontab
docs/       Learning journal and design notes
docker-compose.yml        Local dev — Qdrant only
docker-compose.prod.yml   Production — nginx, backend, qdrant, certbot
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

Open http://localhost:5173 and ask a question. Vite proxies `/api` to the
backend on :8000, mirroring what nginx does in production — so the client
code carries no environment branch.

## Deployment

Live at [trendlens.adil9.tech](https://trendlens.adil9.tech) on a single
VPS. Four containers, only nginx publishing ports:

| Service | Role | Exposure |
|---|---|---|
| nginx | TLS, static files, `/api` proxy, rate limiting | 80/443 |
| backend | FastAPI + uvicorn | internal only |
| qdrant | vector store | internal network only |
| certbot | Let's Encrypt renewal loop | — |

```bash
cp .env.example .env               # set DOMAIN and CERTBOT_EMAIL
cp backend/.env.example backend/.env   # set OPENAI_API_KEY
docker compose -f docker-compose.prod.yml up -d --build

# one-time certificate (--entrypoint certbot bypasses the renewal loop)
docker compose -f docker-compose.prod.yml run --rm --entrypoint certbot certbot \
  certonly --webroot -w /var/www/certbot -d "$DOMAIN" \
  --email "$CERTBOT_EMAIL" --agree-tos --no-eff-email
docker compose -f docker-compose.prod.yml restart nginx

crontab deploy/crontab.example     # hourly ingest :00, embed :05
```

The frontend is served from the same origin as the API, so there's no CORS
to configure and no `BASE_URL` env var. Design rationale — including the
network segmentation and three deployment bugs that passed every
validation check — is in [backend/Design.md](backend/Design.md#9-deployment).

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
UI) is built, hand-evaluated (15 curated queries, see
[backend/readme.md](backend/readme.md#evaluation) for scores), covered by CI,
and deployed. Still open: event-driven ingestion, scheduled digests,
deploy-on-merge, backups, and cost caps on the public API — see the
[Design Document](backend/Design.md) for the full list.

## License

MIT
