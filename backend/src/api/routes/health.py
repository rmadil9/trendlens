import logging

from fastapi import APIRouter, Depends, Response, status
from qdrant_client import QdrantClient

from src.api.dependencies import get_qdrant
from src.storage.vector_store import COLLECTION

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health(response: Response, qdrant: QdrantClient = Depends(get_qdrant)) -> dict:
    """Liveness plus dependency check.

    This previously returned a static {"status": "ok"} — which meant it reported
    healthy with Qdrant face-down, since nothing it did could observe the
    difference. A health check that cannot fail carries no information: the
    container's HEALTHCHECK, and anything watching this endpoint, would keep
    seeing green through a total outage.

    Checking the collection specifically, rather than just opening a connection,
    is deliberate. Qdrant being reachable is not the same as Qdrant holding the
    collection this app queries — a fresh volume or a failed migration produces
    a perfectly responsive server with nothing in it.
    """
    checks = {"qdrant": "ok"}

    try:
        info = qdrant.get_collection(COLLECTION)
        checks["collection"] = COLLECTION
        checks["points"] = info.points_count
    except Exception as e:
        logger.warning("Health check failed against collection %r: %s", COLLECTION, e)
        checks["qdrant"] = "unreachable"
        checks["collection"] = COLLECTION
        # 503, not 200-with-a-sad-body. Orchestrators, load balancers, and
        # Docker's HEALTHCHECK all key off the status code; a body they don't
        # parse saying "degraded" is invisible to every one of them.
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", **checks}

    return {"status": "ok", **checks}
