# TrendLens

A time-weighted RAG system that ingests tech news from multiple sources
and lets you ask questions like *"What's new in AI this week?"* — getting
synthesized, source-cited answers grounded in recent articles.

![Demo](docs/demo.gif)   <!-- Add after MVP -->

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

![Architecture Diagram](docs/architecture-diagram.png)

See [DESIGN.md](docs/DESIGN.md) for detailed design decisions,
tradeoffs, and engineering reasoning.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key

### Run locally
```bash
git clone https://github.com/yourusername/trendlens.git
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
```bash
docker compose --profile production up --build
```

## Live Demo

🔗 [trendlens.yourdomain.com](https://trendlens.yourdomain.com)
<!-- Add after deployment -->

## Evaluation

I tested the system against 15 curated queries across 5 categories
(basic retrieval, time-weighting, specificity, edge cases, answer
quality). Results:

| Metric | Score |
|---|---|
| Retrieval Precision@5 | --% |
| Time-filter Accuracy | --% |
| Answer Faithfulness | --% |
| Citation Accuracy | --% |

<!-- Fill after running eval -->

See [eval/test_queries.md](backend/eval/test_queries.md) for the
full test set and [eval/results/](backend/eval/results/) for
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
- [ ] Ingestion pipeline (RSS → clean text → chunks)
- [ ] Embedding + Qdrant storage
- [ ] Retrieval with time-weighting
- [ ] Generation with citations
- [ ] API endpoints
- [ ] Web UI
- [ ] Evaluation
- [ ] Event-driven ingestion (RabbitMQ)
- [ ] Scheduled digests
- [ ] UI polish
- [ ] CI/CD (GitHub Actions)

## Design Document

The full engineering thinking behind this project — every decision,
tradeoff, and deliberate omission — is documented in
[docs/DESIGN.md](docs/DESIGN.md).

## License

MIT









