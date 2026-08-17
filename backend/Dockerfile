# syntax=docker/dockerfile:1

# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — builder: dependencies + model weights
#
# Everything expensive happens here: the ~1GB torch/transformers/onnxruntime
# install, and the model downloads. None of the build tooling survives into the
# runtime image — that's the entire point of splitting the stages.
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Compilers for any dependency that ships an sdist rather than a wheel. These
# add ~300MB and are discarded with this stage.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

# A venv rather than system site-packages: it gives the runtime stage exactly
# one directory to copy, instead of hunting scattered dist-info across
# /usr/local/lib.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copied alone, before the source, so a code change doesn't invalidate this
# layer — the slowest step in the build shouldn't rerun for a one-line edit.
# requirements.txt carries its own --extra-index-url for the CPU torch wheel.
COPY requirements.txt .
RUN pip install -r requirements.txt

# ── Bake the model weights ────────────────────────────────────────────────────
# Both models lazily download on first use (reranker.py:_get_model,
# sparse_embedder.py:_get_model). Left to runtime that means two problems:
# a multi-second stall on the first query after every deploy, and a hard
# dependency on HuggingFace being reachable for the app to serve at all.
# Downloading at build time converts both into a cost paid once, here.
ENV HF_HOME=/opt/models/hf \
    FASTEMBED_CACHE_PATH=/opt/models/fastembed

RUN python -c "\
from sentence_transformers import CrossEncoder; \
from fastembed import SparseTextEmbedding; \
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2'); \
SparseTextEmbedding(model_name='Qdrant/bm25'); \
print('model weights cached')"


# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — runtime
#
# Starts from a clean slim base. Inherits no compilers, no pip cache, no apt
# lists — only the venv and the model weights are carried across.
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/opt/models/hf \
    FASTEMBED_CACHE_PATH=/opt/models/fastembed \
    HF_HUB_DISABLE_TELEMETRY=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# PYTHONUNBUFFERED matters more than it looks: without it Python block-buffers
# stdout when it isn't a TTY, so `docker logs` shows nothing until the buffer
# fills. Debugging a container that appears to log nothing usually ends here.

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/models /opt/models

# Non-root: a container escape shouldn't hand over root on the host kernel.
RUN useradd --create-home --uid 10001 app

WORKDIR /app

# Application code last — it changes most often, so it sits in the cheapest
# layer to rebuild.
COPY --chown=app:app src/ ./src/
COPY --chown=app:app scripts/ ./scripts/
COPY --chown=app:app eval/ ./eval/

# SQLITE_PATH defaults to ./data/trendlens.db. The directory is created and
# owned here so the volume mounted over it at runtime inherits correct
# ownership rather than materialising as root-owned and unwritable.
RUN mkdir -p /app/data/logs && chown -R app:app /app/data

USER app

EXPOSE 8000

# Uses the venv's Python rather than curl — no extra package needed in the
# runtime image just to answer "is it up?".
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else sys.exit(1)"

# No --reload: that's a development affordance which watches the filesystem and
# costs a process. Workers stay at 1 deliberately — see docker-compose.prod.yml.
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
