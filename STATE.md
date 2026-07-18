# Loop State — My Project

Last run: never

## High Priority (loop is acting or waiting on human)

- **Failing test**: `tests/test_day2.py::TestVectorStore::test_upsert_adds_points` fails on current `master` (22 passed, 1 failed, run 2026-07-16). Assertion `after >= before + len(embedded)` gets `1030 >= 1031` → false. Likely cause: `chunk_store.py`'s deterministic point ID (`uuid5` from `url + chunk_index`) makes upsert idempotent, and the local Qdrant volume already persists this test's fixed test URL from a prior run, so the "add" is a no-op. Probably a test-isolation issue, not a functional regression — needs a human to confirm and either give the test a unique URL per run or point tests at an ephemeral collection. Effort: small (~30 min).
- **"today" time-window may return zero results**: `backend/eval/results/run_20260713T104831Z.md` shows the default `today` window returning 0 retrieved chunks for basic queries; the companion eval file is literally titled "worked around stale-corpus today-window". Corpus's newest articles are dated ~2026-07-01–07-03 vs. eval run on 2026-07-13, so `today`/`week` chips had nothing to retrieve. No cron/scheduler for `backend/scripts/cron/run_ingest.sh` / `run_embed.sh` is visible in this repo (not in docker-compose.yml) — unclear if ingestion is running on a schedule at all. Needs human to confirm ingestion cadence and current corpus freshness; if `today`/`week` are still empty for users right now, that's a user-facing bug. Effort: investigation, ~1h.
- **Eval scoresheet is stale vs. shipped architecture**: `backend/eval/results/scoresheet.md` only scores `run_20260703T122508Z.md`, which predates hybrid search + reranker (shipped 2026-07-13, commit `f3f05ad`). A newer run exists (`run_20260713T105006Z_hybrid_month.md`, spot-checked and looks materially better — clean citations, no dual-mode refusal) but was never scored against `SCORING.md`. Can't confirm whether the old #7 finding (weak retrieval / wrong citation on specificity queries) is fixed. Suggested action: score the 07-13 hybrid run and append a new scoresheet. Effort: medium (~1-2h, mostly manual rubric scoring).

## Watch List

- Old scoresheet #7 (weak retrieval, wrong citation on "Alibaba/Claude cloning" query) — status unknown post-hybrid-search; revisit once a new scoresheet exists for the 07-13 run.
- Old scoresheet #9 (possible hallucination on broad "what's new in tech" query) — already flagged low-confidence/unverifiable by the original scorer; no action unless corroborated.
- `prompt.py` still says "bullets not more than 3-5 or short paragraphs" (line 47) — old scoresheet #13 noted the model sometimes ignores an explicit "one paragraph" ask; minor/cosmetic, low priority.
- Repo root has several untracked files not yet committed: `.claude/`, `AGENTS.md`, `LOOP.md`, `STATE.md`, `loop-budget.md`, `loop-constraints.md`, `loop-run-log.md`. Flagging so it isn't lost, not asking the loop to commit anything.
- No CI configured (no `.github/workflows`) and `gh` CLI isn't available in this environment — loop has no CI/PR/issue signal to triage from; local git + eval/test artifacts are the only visibility.

## Recent Noise (ignored this run)

---
Run log: —