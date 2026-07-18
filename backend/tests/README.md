# TrendLens Test Suite

This suite is divided into fast, deterministic **Unit Tests** (no network/external database) and **Integration Tests** (requires a running Qdrant instance and OpenAI API key).

## Running Tests

- **Unit tests only (CI default):** `pytest -m "not integration"`
- **Integration tests only:** `pytest -m "integration"`
- **All tests:** `pytest`

## Unit Tests

- `test_article_store.py`: Tests SQLite schema, duplication checks, and embedding queues using an in-memory database.
- `test_cleaner.py`: Verifies HTML tag stripping and short-article rejection logic.
- `test_fetcher.py`: Tests RSS date parsing and entry extraction with mocked HTTP calls.
- `test_ingestion_storage.py`: Tests chunker boundaries, dense embedder payload construction, and Qdrant operations.
- `test_retrieval_components.py`: Tests BM25 sparse logic, vector point construction, and CrossEncoder reranker sorting.
- `test_retriever.py`: Tests the string-to-timestamp time boundary logic (e.g., converting "today" into an epoch).
- `test_sources.py`: Validates the URL-based source deduplication engine.

## Integration Tests (`@pytest.mark.integration`)

- `test_retriever.py`: End-to-end semantic pipeline test validating Dense + Sparse + RRF fusion + CrossEncoder Reranking using live Qdrant and OpenAI.

## Remaining Test Gaps (Suggested Next Steps)

- **API Endpoint Tests:** Needs FastAPI `TestClient` to test route behavior for `/api/query` and `/health`.
- **Generation & Prompting:** Mock the GPT-4o-mini generation call to ensure context injection and citation assembly logic is flawless.
- **Full Pipeline E2E:** A complete integration test pushing an actual RSS XML down the entire ingestion pipeline to final Qdrant storage.
