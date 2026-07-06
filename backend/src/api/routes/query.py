import logging

from fastapi import APIRouter, Depends, HTTPException
from qdrant_client import QdrantClient

from src.api.dependencies import get_qdrant
from src.api.models.request import QueryRequest
from src.api.models.response import QueryResponse, Source
from src.generation.generator import generate_answer
from src.generation.prompt import NO_RELEVANT_INFO_MESSAGE
from src.retrieval.retriever import retrieve
from src.retrieval.sources import dedupe_sources

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(body: QueryRequest, qdrant: QdrantClient = Depends(get_qdrant)) -> QueryResponse:
    # Depends(get_qdrant) tells FastAPI: call get_qdrant(request) and pass the result
    # here as `qdrant`. This is dependency injection — the endpoint never calls get_client()
    # itself, so it stays testable (tests can inject a fake client via Depends override).
    try:
        chunks = retrieve(body.question, qdrant, time_window=body.time_window)
        answer = generate_answer(body.question, chunks)
        # No sources when the model found nothing relevant — the chunks were
        # retrieved but the LLM judged them irrelevant, so citing them would
        # be misleading.
        sources = [] if answer.strip() == NO_RELEVANT_INFO_MESSAGE else _build_sources(chunks)
        return QueryResponse(answer=answer, sources=sources)
    except Exception as e:
        logger.exception("Query failed for question=%r", body.question)
        # Re-raise as 500 so the client gets a proper JSON error, not an HTML traceback
        raise HTTPException(status_code=500, detail="Internal server error") from e


def _build_sources(chunks: list[dict]) -> list[Source]:
    # dedupe_sources is the single source of truth for "what counts as a
    # source" (dedup by URL) — the CLI's printed source list is built from
    # the same function, so the two can never disagree.
    return [Source(**s) for s in dedupe_sources(chunks)]
