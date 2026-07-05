# TrendLens — Design Document

## 1. Problem Framing

**Problem statement:** Keeping up with tech/AI news means either reading raw
search-engine links with no synthesis, or asking a chat model that has a
training cutoff and no live grounding in what's actually happening this
week. TrendLens continuously ingests tech news from RSS, embeds it, and
answers natural-language questions with time-aware, multi-source, cited
synthesis instead of a link dump or a stale guess.

**Target user persona:** A technically curious reader (engineer, PM,
hobbyist) who wants a fast, source-backed pulse-check on a specific topic
("What's new with Anthropic?") without reading 5-10 articles themselves,
and who cares whether an answer is actually grounded, not just fluent.

**Success criteria:**
- Ingests from multiple reputable RSS sources on a schedule without manual
  intervention (see `scripts/cron/`)
- Answers are grounded only in retrieved chunks — verified by an eval, not
  just "it looks right" (see section 6)
- Time phrasing in the question measurably changes what's retrieved
  ("this week" vs. no time phrase produce different chunk sets)
- Every claim in an answer is traceable to a specific source + date
- Quality is demonstrable with real numbers, not just a demo that happens
  to work on the day someone watches it

**Out of scope, and why:**
- User auth / multi-tenancy — single-user portfolio demo, no access
  control need
- Hybrid (dense+sparse) retrieval — dense-only is sufficient for tech-news
  vocabulary; deferred to section 11
- Paywalled / non-RSS sources — RSS is free, structured, and reliable
  enough; scraping paywalls adds fragility for little corpus value
- Real-time/streaming ingestion — hourly cron is good enough for a news
  digest use case; event-driven (RabbitMQ) is a deferred post-MVP upgrade
- Multi-turn conversation memory — every query is stateless; adding memory
  is scope creep for an MVP focused on single-shot grounded QA

## 2. Scope and MVP Definition

**MVP definition:** Ask a natural-language question about recent tech news
and get a synthesized, time-aware, source-cited answer grounded in an
auto-updating RSS corpus.

**Feature buckets:**

| Bucket | Features |
|---|---|
| MVP (built) | RSS ingestion (6 feeds), HTML cleaning + URL dedup, recursive chunking, OpenAI embeddings, Qdrant storage, time-filtered dense retrieval, GPT-4o-mini generation with citations, FastAPI backend, React frontend, cron-based auto-refresh (ingest + embed as two separate jobs), hand-scored eval harness |
| Post-MVP (deferred, reasoned about, not built) | RabbitMQ event-driven ingestion (listed in the decisions log as the eventual replacement for cron), hybrid/reranking retrieval, query rewriting, LLM-as-judge eval, scheduled digest emails, CI/CD, production Docker build |
| Skipped (not planned) | User auth, multi-tenancy, paywalled-source scraping, semantic response caching, streaming token-by-token responses |

**Build order** (matches `docs/learning.md` and commit history):
Day 1 — ingest + clean (RSS → SQLite) → Day 2 — chunk + embed + store
(SQLite → Qdrant) → Day 3 — retrieval + generation (the RAG core) →
Day 4 — FastAPI + React + cron automation → Day 5 — eval, one measured
iteration, polish.

## 3. Architecture

**Components:**

| Component | Responsibility |
|---|---|
| `ingestion/feeds.py` | Static list of RSS sources |
| `ingestion/fetcher.py` | Polls a feed, extracts or fetches full text, filters junk |
| `ingestion/cleaner.py` | HTML → plain text, strips paywalled/stub articles |
| `storage/article_store.py`, `schema.py`, `database.py` | SQLite persistence — dedup by URL, embed-queue tracking via `is_embedded` |
| `ingestion/chunker.py` | Splits article text into overlapping, word-bounded chunks |
| `ingestion/embedder.py` | OpenAI embeddings, batched, lazily-initialized client |
| `storage/vector_store.py` | Qdrant collection lifecycle, idempotent upsert via deterministic point IDs |
| `ingestion/pipeline.py` | Orchestrates chunk → embed → upsert for unembedded rows |
| `retrieval/retriever.py` | Parses time phrase → filtered vector search |
| `retrieval/sources.py` | Dedupes chunks into a canonical source list (shared by API and CLI) |
| `generation/prompt.py` | Builds system/user prompt from chunks + question |
| `generation/generator.py` | Calls GPT-4o-mini with retry, returns the answer string |
| `api/main.py`, `routes/`, `models/`, `dependencies.py` | FastAPI HTTP layer, DI for the Qdrant client |
| `frontend/` | React UI — query box, answer panel, citation list |
| `eval/` | Offline evaluation harness (separate from the running app) |

**Data flow — ingestion path:**
`run_ingest.sh` (cron, hourly at :00) → `seed_feeds.py` polls each RSS feed
→ fetch + clean → insert into SQLite with `is_embedded=0` (duplicates
silently skipped via the `url` UNIQUE constraint) → `run_embed.sh` (cron,
hourly at :05, a fixed 5-minute buffer after ingest) → `pipeline.py` pulls
all `is_embedded=0` rows → chunk → embed (OpenAI) → upsert into Qdrant →
flip `is_embedded=1`.

**Data flow — query path:**
User question (React UI or CLI) → `POST /query` → `parse_time_window()`
resolves a date cutoff from the question text → `embed_text()` → Qdrant
search filtered to that cutoff, top-K=5 → `build_prompt()` assembles
system + user messages → GPT-4o-mini → `dedupe_sources()` → JSON
`{answer, sources}` → rendered in React.

**Failure boundaries:**

| Failure | Handling |
|---|---|
| RSS feed down or malformed | Logged (`feedparser`'s `bozo` flag), that feed is skipped, other feeds continue |
| Article fetch fails, or text is too short (paywall/stub) | Article silently dropped, never inserted |
| Duplicate URL | Silently skipped via SQLite UNIQUE constraint — `insert_article()` returns `False` |
| Chunk/embed fails for one article | Caught in `pipeline.py`; that article stays `is_embedded=0` and is retried on the next cron run, rest of the batch is unaffected |
| OpenAI chat completion transient failure (rate limit, timeout, 5xx) | `tenacity` retry, 3 attempts, exponential backoff, in `generator.py` |
| OpenAI embedding call transient failure | **No retry wrapper** — `embedder.py` has no `tenacity` decorator, unlike `generator.py`. Inconsistent; a transient failure here currently propagates and fails the whole ingestion run or query |
| No chunks in the requested time window | `retrieve()` returns `[]`, `generate_answer()` returns a canned "I don't know" message — no crash, no hallucination |
| Qdrant unreachable at API startup | `ensure_collection()` in the FastAPI `lifespan` raises — the app fails to start loudly rather than serving in a broken half-up state |
| Exception inside `/query` | Caught, logged with traceback, client gets a clean `500` JSON error instead of a raw traceback |

**Integration seams (swappable):**
- **Embedding model** — isolated behind `embed_text()`/`embed_chunks()`;
  the only other coupling point is the `DIMENSIONS` constant feeding
  Qdrant's collection config. Swapping to a local model touches 2 files.
- **LLM** — single `MODEL` constant and single call site in
  `generator.py`.
- **Vector store** — `vector_store.py` is the only module that imports the
  `qdrant_client` SDK directly; `retriever.py` and `pipeline.py` never do.
- **Scheduling** — currently OS cron + `flock` shell scripts.
  `feeds.py`/`pipeline.py` have no knowledge of *how* they're invoked, so
  the planned RabbitMQ swap only touches the two shell entrypoints.

**Architecture diagram:** referenced in `readme.md` as
`docs/architecture-diagram.png` but **the file doesn't exist yet** — not
fillable by reading the repo, needs to actually be drawn.

**Deferred components, and why:** RabbitMQ (cron is simpler and sufficient
at this volume — event-driven ingestion only pays off once feed volume or
latency requirements justify the operational overhead of a broker);
hybrid/sparse retrieval and reranking (dense-only has been sufficient per
the eval — see section 6 — revisit if named-entity precision, e.g. query
#7, stays weak after more targeted fixes); query rewriting (adds latency
and another LLM call for a problem that a better prompt or a rerank step
might solve more cheaply first).

## 4. Data Strategy

**Data sources:** 6 RSS feeds, chosen for reliability over coverage —
Ars Technica, TechCrunch, The Verge, Hacker News, MIT Technology Review,
Wired (`src/ingestion/feeds.py`). All are major outlets with stable,
long-lived RSS endpoints. Newsletter sources (mentioned as a possible
tier-2 source in earlier planning) were never added — RSS alone met the
corpus-freshness bar for the eval, so that tier was skipped rather than
built and unused. Hacker News RSS is a special case: it gives front-page
links, not full article text, so `fetcher.py` falls back to fetching and
cleaning the linked page for that feed.

**Ingestion pipeline (6-step flow):**
1. Poll a feed with `feedparser`; on a malformed feed, log a warning and
   continue rather than crash the whole run
2. For each entry, prefer inline full text from the feed (`content` or
   `summary` field) — cheaper and faster than a second HTTP request
3. If no usable inline text, fetch the article URL directly and clean the
   HTML (`cleaner.html_to_text` strips nav/header/footer/script/style tags)
4. Reject anything under 200 characters after cleaning — catches
   paywalled stubs and empty pages (`cleaner.is_too_short`)
5. Insert into SQLite; the `url` UNIQUE constraint does dedup for free —
   `insert_article()` just catches the `IntegrityError` and reports "skip"
6. New rows land with `is_embedded=0`, making them visible to the separate
   embed cron without ingestion ever touching Qdrant directly

**Chunking approach:** Recursive splitting via
`langchain_text_splitters.RecursiveCharacterTextSplitter`, 500-word chunks
with 50-word overlap, using a custom `length_function` that counts words
instead of characters (a cheap proxy for tokens without needing a real
tokenizer — see `docs/learning.md` Day 2 for the reasoning). Separator
priority is paragraph → line → sentence → word → character, so it only
falls back to a blunt cut when a single sentence exceeds the chunk size,
which is rare in news prose.

**Metadata schema** — SQLite `articles` table (see `src/storage/schema.py`): — SQLite `articles` table (see `src/storage/schema.py`):
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

**Data quality risks and mitigations:**
- *Paywalled/stub content* → `is_too_short()` rejects anything under 200
  chars post-cleaning; imperfect (a 250-char paywall teaser still gets
  through) but catches the obvious cases cheaply
- *Malformed RSS feeds* → `feedparser`'s `bozo` flag is checked and logged;
  the run continues instead of crashing on one bad feed
- *Boilerplate leaking into chunk text* (nav/share-buttons/newsletter
  signup text) → `cleaner.py` strips known non-content tags before
  extraction, but this is tag-based, not content-based — some navigation
  cruft still slipped into chunk previews during the eval run (visible in
  `eval/results/run_*.md`, e.g. "REGISTER NOW Most Popular..." prefixes on
  some TechCrunch chunks). Not corrected yet — a real, minor, observed gap.
- *Same story covered by multiple outlets* (e.g. the Sony PlayStation-disc
  story appeared near-identically across 5 sources in the eval corpus) →
  **not deduped** — `dedupe_sources()` only collapses by exact URL, so
  near-duplicate stories from different outlets both surface as distinct
  retrieved chunks and distinct citations. This is arguably fine (multiple
  independent sources corroborating a claim is a feature, not a bug) but
  it was never a deliberate design decision — worth stating explicitly
  rather than leaving it implicit.

**Retention policy:** Keep everything — no TTL or archival. Chosen because
storage is cheap at this volume and historical queries ("what happened in
AI last year") are a stated (if currently unsupported — see section 6,
query #10) product goal. Revisit if corpus growth becomes a real cost or
retrieval-latency concern (see section 11).

## 5. Retrieval and Generation

**Retrieval approach:** Dense-only vector search (cosine similarity over
`text-embedding-3-small` vectors). No sparse/keyword component and no
similarity threshold — `retrieve()` always returns the top-K nearest
chunks even if the best match is a poor one (this is deliberate for the
eval's edge cases — see query #11/#12 in section 6 — but it's a real
tradeoff: an unrelated top-5 always gets handed to the LLM, and the
refusal guardrail is the *only* thing standing between that and a
hallucinated answer).

**Embedding model:** `text-embedding-3-small` (OpenAI API) over a local
model like `all-MiniLM-L6-v2` — chose retrieval quality over the
zero-marginal-cost of local inference; at this corpus size the API cost is
negligible (see section 7). `DIMENSIONS=1536` is isolated in
`embedder.py` and consumed once by `vector_store.py`'s collection config,
so swapping models later is a two-file change.

**Time-weighted retrieval mechanics:** `parse_time_window()` scans the
question text for keyword phrases ("this week" → 7 days, "this/past/last
month" → 30 days, "today"/"recent" → 1 day, else → `DEFAULT_WINDOW_DAYS`
env var, default 30) and converts that to a Unix cutoff. The cutoff is
applied as a Qdrant `Range` filter **inside** the search call, not as a
post-filter in Python — this guarantees up to K results from the correct
window instead of risking 0 results if the naive top-K-then-filter order
happened to be all-old. Known gap: no "last year"/absolute-date branch —
falls back to the 30-day default silently (see query #10 in section 6).

**Prompt template:** Two-part system/user split (see `prompt.py`):
1. **System prompt** — role framing, "use ONLY the provided articles, no
   training-data knowledge," and the refusal instruction (revised
   2026-07-03 — see Iteration log below)
2. **User prompt** — each retrieved chunk tagged
   `[Article N | Source | Date | URL]` followed by its text, then the
   question, then formatting/citation instructions (cite inline as
   `[Source, Date]`, bold key entities, keep answers to 3-5 bullets or up
   to 2 short paragraphs)

**LLM choice:** `gpt-4o-mini` over `gpt-4o` — cost-effective and, per the
eval, sufficient for grounded synthesis at this task's difficulty; no
observed faithfulness gap that pointed at needing a stronger model.

**Hallucination guardrails:** (a) explicit "use ONLY the provided
articles" instruction, (b) an explicit refusal sentence the model must use
when nothing retrieved is relevant, (c) low temperature (0.2) to bias
toward the provided context over creative extrapolation, (d) citations
built from ground-truth retrieved-chunk metadata rather than parsed out of
the model's free-text output (`sources.py`) — so even if the model
mis-describes a source, the *source list itself* can't be wrong. Known
gap, found during this eval pass: the refusal instruction originally had
no notion of *partial* relevance, causing a dual-mode "partial answer +
refusal" bug — fixed, see Iteration log.

**Configuration parameters:** `RETRIEVAL_K=5`, `TEMPERATURE=0.2`,
`MAX_TOKENS=1024`, `DEFAULT_WINDOW_DAYS=30` — all environment-overridable
except temperature/max_tokens, which are hardcoded constants in
`generator.py` rather than env vars (inconsistent with the others, minor).

**What's deferred:** hybrid (dense+sparse) retrieval, reranking, query
rewriting — see section 3's "Deferred components" for the reasoning.

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

### Iteration log

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

**Failure modes and mitigation:** see section 3's failure boundaries table
— the short version is: ingestion fails soft (skip and log), generation
fails soft (canned "I don't know" / retry-then-raise), the API fails loud
at startup if Qdrant is unreachable (fail-fast over serving broken), and
per-request errors return a clean 500 instead of leaking a traceback.

**Security considerations:**
- *API keys* — `OPENAI_API_KEY` lives in `backend/.env`, which is
  `.gitignore`'d (verified — never committed)
- *Prompt injection* — **not defended against.** Article text is inserted
  directly into the LLM context. A malicious or compromised RSS source
  could include text like "ignore previous instructions and..." inside an
  article body, and nothing currently strips or neutralizes that before
  it reaches the model. The only defense is the system prompt's own
  authority as a chat-API system-role message — which is a soft mitigation,
  not a hard one. Real, currently-accepted risk for an MVP pulling from a
  fixed, reputable set of 6 feeds; would need real mitigation before
  ingesting arbitrary/user-submitted sources.
- *Input validation* — `QueryRequest.not_empty` rejects blank questions,
  but there's no length cap and no rate limiting on `/query`. A large
  question increases prompt-embedding cost proportionally; repeated
  requests have no throttle. Combined with no auth (below), this means
  anyone with network access to the API can spend the owner's OpenAI
  budget with no limit beyond `MAX_TOKENS` per individual call.
- *No authentication* on `/query` — acceptable for a local/portfolio demo,
  a real gap before any public deployment.
- *CORS* — locked to `http://localhost:5173` (the Vite dev server) in
  `main.py`; will need updating for any deployed frontend origin.

**Cost breakdown — estimate, not a billing-dashboard figure** (I don't
have access to your OpenAI usage dashboard; this is computed from known
pricing and the actual token volumes this session generated):
- *Ingestion:* corpus currently at 203 articles / 636 chunks in Qdrant.
  At ~650 tokens/chunk (500 words × ~1.3 tokens/word) and
  `text-embedding-3-small`'s $0.02/1M-token rate, embedding the whole
  corpus so far costs roughly **$0.008** — under a cent.
- *Per query:* ~5 chunks × ~650 tokens + prompt overhead ≈ 3,500 input
  tokens, ~300-400 output tokens on `gpt-4o-mini`. At roughly
  $0.15/1M input + $0.60/1M output, that's **~$0.0008/query** — the two
  15-query eval runs in this session cost on the order of **2-3 cents**
  total.
- **Take this as a rough sanity check, not ground truth** — confirm actual
  spend at platform.openai.com/usage against the project's specific
  API key.

**Cost optimization levers already in place:** `MAX_ARTICLES_PER_RUN` cap
on ingestion (bounds how much gets embedded per cron run — the actual
spend-control knob, since embedding is what costs money, not ingestion
itself), embedding batching (`BATCH_SIZE=100`, one network round-trip
instead of N), `gpt-4o-mini` over `gpt-4o`, `is_embedded` flag preventing
re-embedding already-processed articles, `RETRIEVAL_K=5` keeping prompts
small. Not yet in place: cost alerting/budget caps (listed in section 11
as a scale-time addition).

## 8. Developer Experience

**Project structure rationale:** `src/` is split by pipeline stage
(`ingestion/`, `retrieval/`, `generation/`, `storage/`, `api/`), mirroring
the actual data flow rather than by technical layer — makes it obvious
where a change to "how chunking works" vs. "how the API responds" belongs.
`eval/` and `scripts/` sit outside `src/` deliberately: they're operator
tooling (run the pipeline once, ask a question from the CLI, score
quality) rather than part of the running application.

**Configuration strategy:** Environment variables via `.env` +
`os.getenv(..., default)` calls scattered at each point of use (e.g.
`RETRIEVAL_K` in `retriever.py`, `MAX_ARTICLES_PER_RUN` in
`seed_feeds.py`) rather than a single centralized settings object.
**Inconsistency worth knowing about:** `pydantic-settings` is a pinned
dependency in `requirements.txt` but is never actually imported or used
anywhere in `src/` — either a settings-object refactor was planned and not
done, or it's a leftover dependency. Not urgent, but worth either using it
or dropping it from `requirements.txt`.

**Abstraction decisions:**
- `src/storage/schema.py` holds DDL only, separate from `database.py`'s
  connection management — keeps schema changes and connection lifecycle
  independently testable/reviewable
- `retrieval/sources.py`'s `dedupe_sources()` is the single source of
  truth for "what counts as a cited source," consumed identically by both
  the API response (`query.py`) and the CLI (`scripts/ask.py`) — so the
  two can't silently disagree
- Citations are assembled from retrieved-chunk metadata, never parsed from
  the model's free-text output — parsing model output for structured data
  is fragile; ground-truth metadata isn't

**Logging approach:** Per-module `logging.getLogger(__name__)`, level
configured once per entrypoint (`INFO` for the API/pipeline/CLI scripts,
`WARNING` for the eval runner specifically so eval output stays about the
answers, not Qdrant/httpx request noise). No log aggregation or structured
logging (JSON logs) — plain text to stdout/files, redirected by the cron
scripts into `data/logs/`.

**Testing strategy:** `tests/test_day2.py` covers chunker, embedder, and
vector-store behavior (chunk sizing, idempotent upsert, metadata
completeness) — solid unit coverage for the ingestion pipeline.
**Real gap:** there is no test coverage for retrieval (`retriever.py`,
including `parse_time_window()`'s keyword matching), generation
(`prompt.py`, `generator.py`), or the API routes. The eval harness
(section 6) is the only thing currently exercising that code path, and
it's a manual, not automated/CI, check.

**Dependency management:** `requirements.txt` with pinned exact versions,
installed into a project-local `.venv`. No lockfile-based tool (Poetry,
uv, pip-tools) — pinned `==` versions in a flat file is simple and
sufficient at this project size.

## 9. Deployment

**Environment setup (local dev) — real, verified working:**
`docker compose up qdrant -d` for the vector store, `uvicorn
src.api.main:app --reload` for the backend, `npm run dev` for the Vite
frontend. This is the actual path exercised to run the eval in this
session.

**Docker architecture — mostly not built yet.** `docker-compose.yml`
currently defines a **single service: Qdrant.** There are no Dockerfiles
for the backend or frontend anywhere in the repo, and `docker-compose.yml`
has no `profiles:` key at all. This means the command in `readme.md`'s
Quick Start —  `docker compose --profile production up --build` — **will
not run as written.** This is the single biggest gap between what the
README promises and what exists; it's the natural next concrete task
before calling deployment "done."

**CI/CD approach:** none. No `.github/workflows/` directory exists — no
automated test run, lint, or eval-on-PR. Section 11 already lists
"automated eval in CI/CD" as a scale-time goal; this section is the
current-state confirmation that it hasn't started yet.

**Demo strategy:** `readme.md` references `docs/demo.gif` and
`docs/architecture-diagram.png` — **neither file exists in `docs/`
yet** (only `docs/learning.md` is there). Both are still todo.

**Observability:** logging only (section 8) — no metrics, tracing, or
alerting. `/health` exists (`api/routes/health.py`) but only returns a
static `{"status": "ok"}` — it doesn't check Qdrant connectivity or SQLite
reachability, so it can report healthy while a dependency is actually
down.

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

> **Draft, not final** — this is meant to be personal reflection, and I
> (Claude) can only draft it from `docs/learning.md` plus this eval
> session, not from what actually surprised *you*. `docs/learning.md`
> has rich Day 1-3 entries but nothing logged for Day 4 (API + frontend +
> cron) or Day 5 (eval) — worth backfilling those before treating this
> section as done, since the best material here is usually the specific
> moment something clicked, and only you have that for Days 4-5.

**Key lessons:**
- Retrieval and generation are separate failure surfaces with separate
  fixes. A bad answer can come from the wrong chunks being retrieved
  *or* the right chunks being retrieved and misused — conflating the two
  wastes debugging time. The eval's per-query breakdown (query #7 vs.
  #3/#15) made this concrete: #7 was a retrieval problem, #3/#15 were a
  prompt problem, and they needed different fixes.
- Filters and rankings are different mechanisms and can disagree without
  either being "wrong." `parse_time_window()` correctly resolved "today"
  and "recent" to the same cutoff, but the two queries still returned
  different chunks — because ranking runs on the literal question
  embedding, not the normalized time phrase. The eval's own documented
  expectation (query #6 "should match #4") was based on not fully
  tracing through this distinction.
- A guardrail instruction needs to cover the partial case, not just the
  binary case. "Refuse if you don't know" sounds complete but silently
  assumes "know" is all-or-nothing — real multi-part questions aren't.
- Idempotency (deterministic Qdrant point IDs from `url + chunk_index`,
  the `is_embedded` flag as a work queue) makes cron-based retry safe by
  construction — a failed run doesn't need special recovery logic, it
  just re-runs.

**What surprised me (per the Day 2-3 notes):** that embeddings are a
one-way transformation — the LLM never sees the vector, only the payload
text stored alongside it; that batching API calls is ~100x faster for
the same cost, because network round-trips dominate, not computation; and
that Qdrant's pre-filter-then-search order matters — filtering after
search risks silently returning 0 results if the top-K-by-similarity all
happen to be outside the time window.

**What I'd do differently next time:** write the eval query set *before*
finishing generation, not after — several of the assumptions baked into
`test_queries.md` (like query #6's "should match #4") turned out to
reflect a mental model of the system that wasn't quite right, and having
the eval exist earlier would have surfaced that during design instead of
during scoring.

**How this transfers:** the retrieval/generation failure-surface split,
the filter-vs-ranking distinction, and "guardrails need to handle partial
cases" are not specific to news RAG — they apply to any system that
retrieves context and then generates conditioned on it.
