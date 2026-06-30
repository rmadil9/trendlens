import logging

from fastapi import APIRouter, Depends, HTTPException
from qdrant_client import QdrantClient

from src.api.dependencies import get_qdrant
from src.api.models.request import QueryRequest
from src.api.models.response import QueryResponse, Source
from src.generation.generator import generate_answer
from src.retrieval.retriever import retrieve

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(body: QueryRequest, qdrant: QdrantClient = Depends(get_qdrant)) -> QueryResponse:
    # Depends(get_qdrant) tells FastAPI: call get_qdrant(request) and pass the result
    # here as `qdrant`. This is dependency injection — the endpoint never calls get_client()
    # itself, so it stays testable (tests can inject a fake client via Depends override).
    try:
        chunks = retrieve(body.question, qdrant)
        answer = generate_answer(body.question, chunks)
        sources = _build_sources(chunks)
        return QueryResponse(answer=answer, sources=sources)
    except Exception as e:
        logger.exception("Query failed for question=%r", body.question)
        # Re-raise as 500 so the client gets a proper JSON error, not an HTML traceback
        raise HTTPException(status_code=500, detail="Internal server error") from e


def _build_sources(chunks: list[dict]) -> list[Source]:
    # Deduplicate by URL — the same article can produce multiple chunks,
    # but we only want one citation per article in the source list.
    seen: set[str] = set()
    sources: list[Source] = []

    for chunk in chunks:
        if chunk["url"] in seen:
            continue
        seen.add(chunk["url"])
        sources.append(
            Source(
                title=chunk["title"],
                url=chunk["url"],
                source=chunk["source"],
                published_at=chunk["published_at"],
            )
        )

    return sources
