#!/usr/bin/env bash
# Cron 2 — embed only (SQLite is_embedded=0 → Qdrant). Scheduled every 60 min,
# minute :05 — a fixed 5-minute buffer after Cron 1 so ingestion has finished
# writing before this queries the table.
#
# flock -n skips this run rather than queuing if a previous embed run is
# still working through a large backlog.
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$BACKEND_DIR"

exec flock -n "$BACKEND_DIR/data/.embed.lock" \
    "$BACKEND_DIR/.venv/bin/python" -m src.ingestion.pipeline \
    >> "$BACKEND_DIR/data/logs/embed.log" 2>&1
