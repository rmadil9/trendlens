import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()  # must run before any module reads OPENAI_API_KEY from the environment

from src.api.routes import health, query
from src.storage.vector_store import ensure_collection, get_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Everything BEFORE yield runs at startup (like @PostConstruct but for the whole app).
    # Everything AFTER yield runs at shutdown.
    # We initialize Qdrant here once — not inside the endpoint — so the connection
    # is reused across every request instead of being recreated each time.
    logger.info("Starting up — connecting to Qdrant")
    qdrant = get_client()
    ensure_collection(qdrant)
    app.state.qdrant = qdrant  # store on app so dependencies.py can read it
    logger.info("Qdrant ready")

    yield  # server is running, handling requests

    logger.info("Shutting down")


app = FastAPI(
    title="TrendLens API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: allow the React dev server to call this API.
# Without this, the browser blocks the request before it even leaves the tab.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)
app.include_router(query.router)
