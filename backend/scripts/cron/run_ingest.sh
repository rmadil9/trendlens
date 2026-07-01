#!/usr/bin/env bash
# Cron 1 — ingest only (RSS → SQLite). Scheduled every 60 min, minute :00.
#
# flock -n on a dedicated lockfile skips this run instead of queuing behind a
# prior one that's still running (e.g. a slow feed) — better than piling up
# overlapping ingests.
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$BACKEND_DIR"

exec flock -n "$BACKEND_DIR/data/.ingest.lock" \
    "$BACKEND_DIR/.venv/bin/python" -m scripts.seed_feeds \
    >> "$BACKEND_DIR/data/logs/ingest.log" 2>&1
