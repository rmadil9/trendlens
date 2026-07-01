# TrendLens — Design Document

## 1. Problem Framing
<!-- From Phase 1 -->
- Problem statement (2-3 sentences)
- Target user persona
- Success criteria (bullet list)
- What's out of scope and why

## 2. Scope and MVP Definition
<!-- From Phase 2 -->
- MVP definition (one sentence)
- Feature buckets (MVP / post-MVP / skipped) with reasoning
- Build order

## 3. Architecture
<!-- From Phase 3 -->
- Component list with one-sentence responsibilities
- Data flow (ingestion path + query path)
- Failure boundaries table
- Integration seams (what's swappable)
- Architecture diagram
- Deferred components and why

## 4. Data Strategy
<!-- From Phase 4 -->
- Data sources (tiered: RSS → newsletters → skip)
- Ingestion pipeline (6-step flow)
- Chunking approach (recursive, 500 tokens, 50 overlap)
- Metadata schema — SQLite `articles` table (see `src/storage/schema.py`):
  - `id` (PK, autoincrement)
  - `url` (`NOT NULL UNIQUE` — sole dedup anchor; no content-hash column)
  - `title`, `source`, `published_at` (ISO-8601 string), `raw_text`
  - `ingested_at` (defaults to insert time)
  - Indexes on `published_at` and `source` for retrieval-time filtering
  - Note: an earlier design used a `content_hash` (SHA-256) column as a
    second dedup anchor alongside `url`. It was removed — URL uniqueness
    alone was sufficient and the extra hash added no dedup value in
    practice.
- Dual storage architecture (Qdrant + SQLite): Qdrant holds chunk
  embeddings + payload for vector search; SQLite holds article-level
  metadata and is the source of truth for dedup (by `url`) and
  time-range filtering
- Data quality risks and mitigations
- Retention policy (keep everything)

## 5. Retrieval and Generation
<!-- From Phase 5 -->
- Retrieval approach (dense, hybrid deferred)
- Embedding model choice and tradeoff
  (text-embedding-3-small: chose API quality over local
  cost savings, parameterized for swap)
- Time-weighted retrieval mechanics
- Prompt template (full structure)
- LLM choice (gpt-4o-mini) and why
- Hallucination guardrails
- Configuration parameters (K=5, temperature=0.2,
  default 30-day window)
- What's deferred (hybrid, reranking, query rewriting)

## 6. Evaluation
<!-- From Phase 6 -->
- What's measured (precision@K, time-filter correctness,
  faithfulness, citation accuracy)
- Test query set (15 queries across 5 categories)
- Eval workflow (manual, spreadsheet-based)
- Results (filled after running eval)
- Iteration log (what changed and what improved)

## 7. Reliability, Security, and Cost
<!-- From Phase 7 -->
- Failure modes and mitigation strategies
- Security considerations (prompt injection, API keys,
  input validation)
- Cost breakdown with actual numbers
- Cost optimization levers

## 8. Developer Experience
<!-- From Phase 8 -->
- Project structure rationale
- Configuration strategy
- Abstraction decisions with reasoning
  (`src/storage/schema.py` holds DDL only, separate from
  `database.py`'s connection management — keeps schema changes and
  connection lifecycle independently testable/reviewable)
- Logging approach
- Testing strategy
- Dependency management

## 9. Deployment
<!-- From Phase 9 -->
- Environment setup (local dev vs. production)
- Docker architecture
- CI/CD approach
- Demo strategy
- Observability

## 10. Decisions Log

A running table of every significant decision:

| Decision | Chosen | Alternatives Considered | Why |
|---|---|---|---|
| Vector store | Qdrant | pgvector, ChromaDB, FAISS | Native metadata filtering for time-weighting |
| Embedding | text-embedding-3-small (API) | all-MiniLM-L6-v2 (local) | Higher quality, small cost acceptable |
| LLM | gpt-4o-mini | gpt-4o, Gemini | Cost-effective, sufficient for synthesis |
| Chunking | Recursive, 500 tokens | Fixed-size, semantic | Respects text structure, predictable size |
| Message broker | RabbitMQ | Redis Streams, Kafka | Reliable delivery, DLQ support, right-sized |
| Frontend | React | Vanilla HTML+HTMX, Streamlit | Polished UX for portfolio demo |
| Retrieval | Dense only | Hybrid (dense+sparse) | Sufficient for tech news vocabulary, hybrid deferred |
| Data retention | Keep everything | TTL-based cleanup | Storage is cheap, enables historical queries |
| Deployment | Manual → GitHub Actions | CI/CD from start | Ship MVP faster, automate once stable |

## 11. What I'd Do Differently at Scale

- Hybrid retrieval for vocabulary coverage
- Qdrant clustering for availability
- Kubernetes for multi-node deployment
- Log aggregation (ELK or CloudWatch)
- Automated eval in CI/CD pipeline
- LLM-as-judge for continuous quality monitoring
- Cost alerting and budget caps on OpenAI
- Rate limiting and user authentication

## 12. What I Learned

<!-- Fill as you build — this is personal reflection -->
- Key lessons from building this system
- What surprised you
- What you'd do differently next time
- How these lessons transfer to other systems
