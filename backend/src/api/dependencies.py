from fastapi import Request
from qdrant_client import QdrantClient


def get_qdrant(request: Request) -> QdrantClient:
    # app.state is a bag FastAPI provides to store anything attached to the app instance.
    # We put the Qdrant client there at startup (see main.py lifespan) so every request
    # can read it here without creating a new connection each time.
    return request.app.state.qdrant
