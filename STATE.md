# Loop State — TrendLens

Last run: 2026-08-18 (manual, during deployment work)

## High Priority (loop is acting or waiting on human)

- **No cost cap on a public, unauthenticated API.** `POST /query` is live at
  `https://trendlens.adil9.tech/api/query` with no auth. nginx rate-limits it
  to 20r/m per IP, which bounds abuse but doesn't prevent it — a single IP can
  spend ~$0.001/query, all day. There is no OpenAI budget alert and no spend
  ceiling configured. This is the largest open risk now that the service is
  public. Suggested action: set a hard usage limit in the OpenAI dashboard
  (outside this repo), and decide whether the demo needs a shared-secret
  header. Effort: small, but needs a human decision on how public this should be.
- **Nothing is backed up.** The Qdrant volume (`trendlens_qdrant_data`) and the
  SQLite DB both live in Docker volumes on a single VPS with no snapshot, no
  export, and no off-box copy. The corpus is re-ingestible from RSS, but only
  going forward — anything older than what the feeds currently serve would be
  permanently lost. Effort: small (a cron'd `qdrant` snapshot + `sqlite3
  .backup` to object storage).
- **No uptime monitoring.** If the stack stops serving, nothing notices. The
  containers have `restart: unless-stopped` and the backend has a HEALTHCHECK,
  but a container stuck in a crashloop, an expired certificate, or a full disk
  would all go unobserved until someone opened the site. Effort: small
  (external ping on `/api/health`, which now returns 503 when degraded).

## Watch List

- **Log rotation.** `logs/ingest.log` and `logs/embed.log` on the VPS grow
  unbounded — hourly cron, no logrotate config. Not urgent, will matter.
- **`MAX_ARTICLES_PER_RUN=5`** means ~120 articles/day. The feeds had a backlog
  at deploy time. Fine steady-state; raise temporarily if the corpus needs to
  catch up.
- **Eval scoresheet is stale vs. shipped architecture.**
  `backend/eval/results/scoresheet.md` only scores `run_20260703T122508Z.md`,
  which predates hybrid search + reranker (shipped 2026-07-13, `f3f05ad`). A
  newer run exists (`run_20260713T105006Z_hybrid_month.md`) but was never
  scored against `SCORING.md`. Now re-runnable against a fresh corpus for the
  first time since July. Effort: medium (~1-2h, manual rubric scoring).
- **Old scoresheet #7** (weak retrieval, wrong citation on the "Alibaba/Claude
  cloning" query) — spot-checked as fixed post-hybrid-search, never formally
  rescored. Revisit with the scoresheet above.
- **`docs/architecture-diagram.png` and `docs/demo.gif`** are referenced by both
  READMEs and neither exists. The live URL partly covers the demo GIF's purpose.
- **`pydantic-settings`** is pinned in `requirements.txt` and imported nowhere.
  Either use it or drop it.
- **No deploy-on-merge.** Deployment is `git pull && docker compose -f
  docker-compose.prod.yml up -d --build` by hand on the VPS.

## Resolved since last run

- ~~Failing `tests/test_day2.py`~~ — that file no longer exists; the suite was
  reorganised into 7 unit files plus integration markers (`backend/tests/README.md`).
  56 unit tests pass.
- ~~"today" time-window returns zero results~~ — root cause was a dead corpus
  (no cron was ever installed; last ingest 2026-07-05). Fixed by the production
  deploy: hourly ingest/embed crontab is now installed and verified on the VPS.
- ~~No CI configured~~ — `.github/workflows/ci.yml` shipped 2026-07-18.
- ~~No production Docker build~~ — 4-container stack live at
  `https://trendlens.adil9.tech` since 2026-08-17. See `Design.md` §9.
- ~~Untracked loop scaffolding at repo root~~ — committed.

## Recent Noise (ignored this run)

---
Run log: `loop-run-log.md`
