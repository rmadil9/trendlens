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

**What's measured:** Precision@5 (of the 5 retrieved chunks, how many are
actually on-topic), time-filter correctness (does the retrieved date range
match what the query's time phrase implies), answer faithfulness (does
every claim in the generated answer trace back to a retrieved chunk), and
citation accuracy (does every inline `[Source, Date]` tag point at a chunk
that was actually retrieved and actually supports the claim it's attached
to). No LLM-as-judge or RAGAS — scored by hand against the rubric in
`eval/SCORING.md`. Deliberately black-box-free at this stage: hand-scoring
15 queries is fast enough not to need automation yet, and automating the
judge before trusting your own judgment on 15 examples just adds a second
thing that can be wrong.

**Test query set:** 15 queries across 5 categories (basic retrieval,
time-weighting, specificity, edge cases, answer synthesis) — see
`eval/test_queries.md` for the rationale behind each one and
`eval/queries.py` for the executable source of truth.

**Eval workflow:** `python -m eval.run_eval` (from `backend/`) runs all 15
queries through the live retrieve → generate pipeline and dumps chunks +
answers + citations to a timestamped file in `eval/results/`. Scoring is
manual against `eval/SCORING.md`'s rubric, recorded in
`eval/results/scoresheet.md`.

**Results** (run `run_20260703T125007Z.md`, post-iteration):

| Metric | Score |
|---|---|
| Retrieval Precision@5 (all 15) | 68% |
| Retrieval Precision@5 (excl. edge cases) | 82% |
| Time-filter Accuracy | 80% (12/15 — 3 expected fails, see below) |
| Answer Faithfulness | 87% (13/15) |
| Citation Accuracy | ~87% |

Time-filter "failures" are all in the edge-case bucket by design: #11-12
are fully off-topic queries with no time-relevant chunks to filter
correctly in the first place, and #10 is a *known, documented* gap —
`parse_time_window()` has no "last year" branch and silently falls back to
the 30-day default. That's a real product gap (queries about older news
silently return recent news instead of an empty/clarifying result) but not
a regression — it's flagged in the query set specifically to keep it
visible instead of letting it hide.

**What retrieval got wrong, and why it's more interesting than the
scores:**

- **Query #7** ("What did Anthropic say about Alibaba's Claude cloning
  attack?") scored 1/5 precision — narrow, named-entity queries pull in a
  lot of same-topic-wrong-story noise (an unrelated Europe heat wave
  article made the top 5 purely on "Anthropic" term overlap in a nearby
  newsletter blurb). The model still answered faithfully by leaning on the
  one good chunk, but mis-cited an unrelated chunk for a specific claim —
  a case where low retrieval precision leaked into citation accuracy.
- **Query #6 vs #4** — the query set originally asserted these should
  return *identical* chunks since `parse_time_window()` treats "recent"
  and "today" as the same 1-day window. They didn't, and that's correct
  behavior, not a bug: the time-window filter was identical in both runs,
  but `retrieve()` ranks by cosine similarity against the *literal query
  text*, and "What happened in AI today?" vs. "What's the recent AI news?"
  embed differently. Fixed the query set's documented expectation rather
  than the code — the code was right, the test's assumption wasn't.
- **Query #10** exposed a second-order failure on top of the known
  time-window bug: instead of noticing that its retrieved evidence was
  from *this week*, not *last year*, and qualifying the answer, GPT-4o-mini
  answered as if the mismatch didn't exist ("Last year, OpenAI was forced
  to update its models..." — describing a story from three days prior).
  The retrieval bug is documented and accepted for MVP; this generation-side
  compounding of it is a good candidate for a future guardrail (e.g. pass
  the resolved time window into the prompt so the model can flag a
  mismatch instead of silently absorbing it).

## Iteration log

**2026-07-03 — partial-relevance answers were falsely triggering the
refusal guardrail.** Queries #3 and #15 (both multi-part questions where
only some retrieved chunks were on-topic) produced a real, well-cited
partial answer *followed by* the exact refusal sentence
("Sorry, I could not find relevant information...") tacked on at the end
— a dual-mode answer that undermines trust in the guardrail (if it fires
even when the model clearly did find something, users learn to ignore it).

Root cause: `prompt.py`'s system prompt told the model when to refuse
*entirely* but never said what to do when only *part* of a multi-part
question was answerable. The model applied the refusal literally to
whatever sub-question it couldn't source, even after already answering the
rest.

Fix: one change, in `src/generation/prompt.py` — added an explicit
instruction to answer the supported parts and silently omit the
unsupported parts, reserving the refusal sentence for when *none* of the
retrieved articles are relevant at all. No retrieval/chunking/K changes.

Before/after (`run_20260703T122508Z.md` → `run_20260703T125007Z.md`):
query #3 and #15 both lost the trailing refusal sentence while keeping
their existing citations unchanged; #9 additionally surfaced two claims
(Ford re-hiring engineers, a stratospheric-internet story) that were
present in the underlying chunk text all along but previously got
excluded by the same over-eager refusal framing. #11 and #12 (fully
off-topic queries) still refused cleanly — the guardrail still fires when
it should, it just no longer fires when it shouldn't. Diffed all 15
answers before/after: zero regressions, 2 clear fixes, 1 improvement as a
side effect.

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
