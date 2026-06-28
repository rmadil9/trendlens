# TrendLens — Learning Journal


---


## Day 1 :- Scaffolding and data ingestion

Scaffolding project directory and structure. 
Initalized config for fetching the data from. 
fetched and cleaned data from url using httpx and beautifulsoup4.



## Day 2: Processing + Storage (Embedding Pipeline)

### Chunking

- Embedding models have a token limit. More importantly, embedding a full article into one vector loses precision — the vector tries to represent too many ideas at once. Smaller focused chunks = more precise retrieval.
- **Overlap exists** so sentences at chunk boundaries don't lose context. Without it, meaning splits across chunks and both sides become orphaned thoughts.
- **Recursive splitting** respects document structure — tries paragraph breaks first, falls back to sentences, then words, then characters as a last resort. A fixed character splitter skips all of that and cuts blindly.
- **Why size chunks in words, not characters?** Characters vary wildly by word length but the model experiences tokens, not characters. Words are a cheap proxy — 1 word ≈ 1.3 tokens for news prose. Setting up a real tokenizer is heavy and unnecessary here.
- If a chunk fits under the limit → accumulate the next piece greedily. If a single piece already exceeds the limit → fall back to a finer separator and split the piece itself.

### Embeddings

- An embedding is a list of numbers (1536 for `text-embedding-3-small`) that represents the *meaning* of text. Similar texts produce vectors that point in the same direction in that 1536-dimensional space.
- **Inference** = running a trained model to get output. Embedding a chunk is inference. Training the model is a separate, much heavier process.
- **Batching** matters — sending 100 chunks in one API call vs 100 individual calls costs the same but is ~100× faster because the network round-trip is the bottleneck, not the computation.
- **Lazy client init** — instantiate the OpenAI client only on first use, not at import time. If you do it at import time, importing the module in a test before env vars are set will crash immediately.
- The API returns results in the same order as inputs — safe to zip chunks and vectors directly.

### Vector Storage (Qdrant)

- Qdrant stores **points**. A point = id + vector + payload. Think of it like a row in SQLite but the primary search is by vector similarity, not column value.
- **Metadata (payload) is essential** — the vector finds which chunks are relevant, the payload tells you what to do with them (show the title, link the URL, filter by date).
- **Cosine distance** measures angle between vectors, ignoring magnitude. Right choice for semantic similarity — a long article and a short article on the same topic should score equally. Dot product is used when magnitude carries meaning (e.g. recommendation confidence).
- **Deterministic UUIDs** — derive the point ID from `url + chunk_index` so the same chunk always gets the same ID. Upsert then becomes idempotent: re-running the pipeline overwrites in place instead of duplicating. We are the dedup mechanism, not Qdrant.
- **Why overwrite instead of skip (unlike SQLite)?** In SQLite, checking for duplicates is free (UNIQUE constraint). In Qdrant, checking costs an extra network call. Overwriting with identical data is harmless and cheaper.
- A **Qdrant Cloud cluster** = a server instance (infrastructure). A **vector cluster** = a natural grouping of semantically similar points that emerges from the math. Same word, completely different meaning.

### Pipeline Architecture

- The order is fixed: SQLite → chunk → embed → upsert. Each step is a pure function that takes the output of the previous one. Easy to test each piece in isolation.
- `published_at` must be stored as a **Unix timestamp (integer)**, not an ISO string. Qdrant's range filter is numeric — tomorrow's time-weighting query won't work on a string.

---

## Day 2: Critical Questions I Asked

These are the questions that took more than one explanation to click — worth revisiting.

**Q: Why count words instead of characters for chunk size?**
Because the model sees tokens, not characters. "Simultaneously" = 14 chars but ~1 word ~1.3 tokens. "AI" = 2 chars, same token count. Characters are a bad proxy. Words are close enough without needing a real tokenizer.

**Q: If the first paragraph is 150 words and the limit is 500 — does the splitter stop or keep filling?**
It keeps filling. It accumulates greedily until the next piece would push it over 500. It never stops early just because it hit a natural boundary.

**Q: 700-word paragraph falls back to sentences. 4 sentences = 470 words, 5th makes it 520 — which does it take?**
4 sentences (470 words). Never exceeds the limit. The 5th sentence starts the next chunk.

**Q: What if a single sentence is 600 words?**
Falls back to word-boundary splitting (`" "`). Cuts that sentence at the 500-word mark. Only reaches character splitting if a single word exceeds 500 characters — basically never in real text.

**Q: Why overwrite in Qdrant instead of skipping duplicates like SQLite does?**
In SQLite, the UNIQUE constraint catches duplicates for free on insert. In Qdrant, checking first requires an extra network call per chunk. Overwriting with identical data costs nothing extra and has zero harm. Different tool, different tradeoff.

**Q: Why url + chunk_index for the UUID — why not just generate a random one?**
Random UUID = different ID every run = duplicates pile up forever. `url + chunk_index` is deterministic — same chunk always hashes to the same ID, so upsert lands on the same slot every time. No duplicates, no extra check needed.

**Q: Qdrant Cloud gave me an option to create a cluster — isn't a cluster the grouping of similar vectors?**
Two different meanings. Qdrant Cloud cluster = a server instance (infrastructure, like renting a machine). Vector cluster = natural grouping of semantically similar points in vector space. Same word borrowed from two different fields.

**Q: What is batching and why does it matter?**
Without batching: 100 chunks = 100 API calls = 100 network round-trips (~200ms each = ~20s total). With batching: 100 chunks = 1 API call = 1 round-trip (~200ms). Same cost, same tokens processed, ~100× faster. The network is the bottleneck, not the computation.

**Q: What is lazy client init and why does it matter?**
If you call `OpenAI()` at import time (top of the file), Python runs it the moment any other file imports your module — even in tests before env vars are loaded. Lazy init wraps it in a function that only runs on first actual use, giving you control over when the env var is read.

---

## Day 2: Terminology

| Term | Plain meaning |
|---|---|
| **Embedding** | A list of numbers representing the meaning of text. Similar texts → similar numbers. |
| **Vector** | The list of numbers itself (1536 floats for text-embedding-3-small). |
| **Inference** | Running a trained model to get output. Opposite of training. |
| **Chunk** | A smaller piece of a larger text, cut to fit within token limits while keeping context. |
| **Overlap** | Repeated tokens at chunk boundaries so neither side loses context. |
| **Recursive splitting** | Splitting strategy that tries coarse separators (paragraphs) before fine ones (characters). |
| **Point** | One record in Qdrant. Has an id, a vector, and a payload (metadata). |
| **Payload** | The metadata attached to a Qdrant point — title, URL, source, published_at etc. |
| **Upsert** | Insert if new, overwrite if ID already exists. |
| **Deterministic UUID** | A UUID derived from fixed inputs — same inputs always produce the same UUID. |
| **Cosine distance** | Similarity metric based on angle between vectors. Ignores length, only cares about direction. |
| **Dot product** | Similarity metric based on angle AND magnitude. Used when vector size carries meaning. |
| **Vector cluster** | Natural grouping of semantically similar points that emerges from the math. Not created manually. |
| **Qdrant Cloud cluster** | A server instance running Qdrant — infrastructure, not a math concept. |
| **Batch** | Sending multiple inputs in one API call instead of one at a time. |
| **Lazy init** | Delaying object creation until first use instead of at import/startup time. |
| **Unix timestamp** | Date/time as an integer (seconds since Jan 1 1970). Required for numeric range filters. |
| **Idempotent** | Running the same operation multiple times produces the same result as running it once. |


