#!/usr/bin/env bash
# Production embed — SQLite is_embedded=0 → Qdrant. Host crontab, hourly at :05.
#
# The 5-minute offset from ingest.sh is the same fixed buffer the local scripts
# use: ingestion should have finished writing before this reads the table.
# It's a heuristic, not a guarantee — but the work queue makes that safe.
# Anything ingest hasn't committed yet simply stays is_embedded=0 and gets
# picked up by the next run.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$REPO_DIR/docker-compose.prod.yml"
LOG_DIR="$REPO_DIR/logs"

mkdir -p "$LOG_DIR"

exec flock -n /var/lock/trendlens-embed.lock \
    docker compose -f "$COMPOSE_FILE" exec -T backend \
    python -m src.ingestion.pipeline \
    >> "$LOG_DIR/embed.log" 2>&1
