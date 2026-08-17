import logging
import os
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

# CORS — defence in depth, not the primary control.
#
# In production the frontend is served from the same origin as this API (nginx
# serves the bundle and proxies /api on trendlens.adil9.tech), so requests are
# same-origin and the browser never runs a CORS check at all. This exists for
# the local split-origin dev case, and so a future split-origin deployment
# fails closed rather than open.
#
# Worth being precise about what the previous allow_origins=["*"] did and did
# not do: CORS is enforced by browsers, not by servers. It never stopped curl or
# a script — those were always able to reach this API. What "*" did allow was
# any website on the internet building a frontend against this backend, funding
# their traffic with this project's OpenAI key. Direct scripted abuse is the
# rate limiter's job (nginx, limit_req); this handles browser-origin abuse.
# The two controls are complementary, not redundant.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)
app.include_router(query.router)
