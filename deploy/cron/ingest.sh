#!/usr/bin/env bash
# Production ingest — RSS → SQLite. Host crontab, hourly at :00.
#
# Same shape as backend/scripts/cron/run_ingest.sh, with one change: there is no
# .venv on the server, so the work runs inside the backend container. Those
# local scripts stay as they are for local development against a host venv.
#
# flock stays on the HOST, not in the container. The lock's job is to stop two
# cron firings from overlapping, and cron is what's being guarded — so the lock
# belongs on the same side as the thing it protects.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$REPO_DIR/docker-compose.prod.yml"
LOG_DIR="$REPO_DIR/logs"

mkdir -p "$LOG_DIR"

# -T disables TTY allocation. Without it `docker compose exec` fails outright
# under cron, which has no terminal attached — a classic "works when I run it,
# silently broken on a schedule" failure.
exec flock -n /var/lock/trendlens-ingest.lock \
    docker compose -f "$COMPOSE_FILE" exec -T backend \
    python -m scripts.seed_feeds \
    >> "$LOG_DIR/ingest.log" 2>&1
