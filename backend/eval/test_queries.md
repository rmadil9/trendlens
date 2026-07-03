# TrendLens Evaluation — Test Query Set

15 queries across 5 categories, grounded in the real ingested corpus as
it stood when this set was written (146 articles, 6 sources, spanning
2026-06-23 → 2026-07-02 — heavy Anthropic/OpenAI/AI-funding coverage,
plus a large multi-article story on Sony discontinuing PlayStation
discs). If you re-run this eval much later, the corpus will have moved
on and some of these may no longer have a live news cycle to retrieve.

The executable source of truth is `eval/queries.py` — this file explains
the *why* behind each query. See `eval/SCORING.md` for how to score results.

## 1. Basic retrieval
Clear, on-topic questions that should have obvious, easy-to-find matches.

1. What's new with Anthropic and Claude?
2. What's happening with Sony and PlayStation physical game discs?
3. What AI startups raised funding recently?

## 2. Time-weighting
Same/similar topic, different time phrasing — tests that the time filter
actually changes which chunks come back.

4. What happened in AI today?
5. What happened in AI this week?
6. What's the recent AI news?
   — Expected: identical results to #4. "recent" is a synonym for "today"
     in `parse_time_window()`. Diverging results means that fix regressed.

## 3. Specificity
Narrow/named-entity queries vs. one deliberately broad query.

7. What did Anthropic say about Alibaba's Claude cloning attack?
8. Tell me about Sony's disc production shutdown timeline
9. What's new in tech this week?
   — Deliberately broad/generic. Stress-tests whether synthesis stays
     coherent instead of turning into an unfocused grab-bag.

## 4. Edge cases
Designed to probe known weak points, not to "pass."

10. What happened in AI last year?
    — Expected to FAIL correctly: `parse_time_window()` has no "last year"
      branch, so this silently falls back to the 30-day default instead
      of actually filtering to last year. Scoring this a pass would be
      wrong — the point is to document the gap.
11. What did NVIDIA announce this week?
    — NVIDIA never appears in the corpus. `retrieve()` has no similarity
      threshold, so Qdrant still returns top-5 *unrelated* chunks. Tests
      whether the generation guardrail refuses instead of loosely
      hallucinating around them.
12. What's the weather forecast for next week?
    — Fully off-topic. Same guardrail test, different angle.

## 5. Answer quality / synthesis
Requires pulling facts from 2+ articles into one coherent answer.

13. Summarize this week's Anthropic news in one paragraph
14. Walk me through Sony's PlayStation disc discontinuation story
15. What AI funding rounds happened this week and how much did each raise?
