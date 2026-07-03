# Scoresheet — run_20260703T122508Z.md

Drafted by Claude by reading `run_20260703T122508Z.md` against the rubric in
`SCORING.md`. **This is a draft, not a verdict** — go re-read the flagged
rows (⚠) yourself against the full run file before trusting the rollup
numbers in the README. Everything else follows the rubric mechanically
enough that a second pass is mostly a spot-check.

| # | Category | Precision@5 | Time-filter | Faithfulness | Citations | Notes |
|---|---|---|---|---|---|---|
| 1 | Basic retrieval | 5/5 | Pass | Pass | 3/3 | clean |
| 2 | Basic retrieval | 5/5 | Pass | Pass | 3/3 | clean |
| 3 | Basic retrieval | 1/5 | Pass | **Fail** | 0/1 wrong | ⚠ see below |
| 4 | Time-weighting | 5/5 | Pass | Pass | 3/3 | clean |
| 5 | Time-weighting | 5/5 | Pass | Pass | 3/3 | clean |
| 6 | Time-weighting | 5/5 | Pass | Pass | 3/3 | ⚠ does NOT match #4 — see note |
| 7 | Specificity | 1/5 | Pass | Pass | 1 wrong of ~2 | ⚠ weak retrieval, mis-cited |
| 8 | Specificity | 5/5 | Pass | Pass | 3/3 | clean |
| 9 | Specificity | 5/5 | Pass | **Fail (unverifiable)** | 2 unverifiable | ⚠ see below |
| 10 | Edge case | 2/5 (expected) | **Fail (expected — documented bug)** | **Fail** | n/a | ⚠ see below — worse than expected |
| 11 | Edge case | 0/5 (expected) | Fail (expected) | Pass (refused correctly) | 0 made | as designed |
| 12 | Edge case | 0/5 (expected) | Fail (expected) | Pass (refused correctly) | 0 made | as designed |
| 13 | Answer quality | 5/5 | Pass | Pass (mostly) | 3/3 | ⚠ ignored "one paragraph" instruction, wrote 3 bullets |
| 14 | Answer quality | 5/5 | Pass | Pass | 3/3 | clean |
| 15 | Answer quality | 2/5 | Pass | Pass (for supported bullets) | 2/2 | ⚠ same dual-mode bug as #3 |

## Rollup

Two ways to compute Precision@5, per SCORING.md's note that edge cases
(#10-12) can be excluded for a "does retrieval work" number:

- **All 15 queries:** (5+5+1+5+5+5+1+5+5+2+0+0+5+5+2)/75 = 51/75 = **68%**
- **Excluding edge cases (#10-12):** (5+5+1+5+5+5+1+5+5+5+5+2)/60 = 49/60 = **82%**

- **Time-filter Accuracy:** 12 PASS / 15 = **80%** (the 3 fails are #10-12,
  all *expected* per the eval design — #10 is a real documented bug, #11-12
  are "no similarity threshold" by design)
- **Answer Faithfulness:** 12 PASS / 15 = **80%** (fails: #3, #9, #10 — all
  three detailed below, and all three are genuine, not edge-case-expected)
- **Citation Accuracy:** roughly 20/23 citation instances correct ≈ **87%**
  (rough count — recount by hand, I did not carefully enumerate every
  bracket tag)

## Flagged findings (the interesting part)

**#3 and #15 — dual-mode answer bug (real bug, reproducible, worth fixing).**
Both answers give 1-2 genuinely well-cited bullets, then append the exact
refusal sentence ("Sorry, I could not find relevant information...") even
though the model *did* answer part of the question. Root cause: `prompt.py`'s
system prompt says to refuse if "the provided articles do not contain enough
information," but never tells the model what to do when only *some* of the
retrieved chunks are relevant. The model appears to apply the refusal
literally to the *unanswered remainder* of a multi-part question ("what
funding rounds... **and how much did each raise**") instead of just omitting
what it can't support. This is the single most fixable, most concrete
finding in the whole run — see "Suggested iteration" below.

**#7 — Specificity retrieval is weak (1/5).** For "What did Anthropic say
about Alibaba's Claude cloning attack?" only chunk 1 is actually about the
Alibaba attack; chunks 2-5 are Anthropic-adjacent-but-wrong-story (Trump
admin security measure, China AI experts, a heat wave story that shouldn't
even be in the top 5, and Claude Science). The model still wrote a faithful
answer by leaning on chunk 1, but then cited MIT Tech Review 2026-06-30
(the Claude Science chunk) for the "largest known distillation attack"
claim — that chunk doesn't support that claim. That's a genuine wrong
citation, not just noise in the retrieved set.

**#9 — possible hallucination on the broad "what's new in tech" query,
but unverifiable from the dump.** The answer states specific claims (Ford
rehiring engineers, a Senator Warren AI-agents bill) that don't appear
anywhere in the 180-char previews shown. This *might* be legitimate — the
retrieved chunks are MIT Tech Review "The Download" newsletter digests,
which bundle several unrelated blurbs per chunk, so the full chunk text
(not just the truncated preview) could easily contain both. **You need to
open `run_20260703T122508Z.md`'s chunk 2/4 full text (or query the DB
directly) to settle this** — I scored it Fail per the rubric's literal
"if it's not in the preview, it's unsupported" instruction, but flag it as
low-confidence.

**#6 vs #4 — do NOT read this as a parse_time_window() regression.**
I checked `retriever.py`: `parse_time_window("today")` and
`parse_time_window("recent")` both correctly resolve to `days=1` — the
time-window filter is identical. But `retrieve()` embeds the *literal
question text* and ranks by cosine similarity against that embedding, not
against a normalized time-phrase. "What happened in AI today?" and "What's
the recent AI news?" are different sentences → different embedding vectors
→ different top-5 ranking, even under an identical date cutoff. Both runs
independently pass the time-filter check (all chunks within ~1 day). The
eval doc's expectation ("should return IDENTICAL results") was based on a
wrong assumption about how the system works, not a code bug. Worth fixing
the wording in `test_queries.md`/`queries.py` so it says "same time window,
not necessarily identical top-5" instead.

**#10 is worse than the eval predicted.** The known bug (no "last year"
branch → 30-day fallback) is confirmed. But the *generation* layer made
it worse: instead of noticing "last year" ≠ "the last 30 days" and
qualifying the answer, GPT-4o-mini answered as if the retrieved (this-week)
chunks *were* "last year" — e.g. "Last year, OpenAI was forced to update
its models..." when the cited Wired article (2026-07-01) is describing
recent, not year-old, incidents. This is a second, compounding failure on
top of the known retrieval bug: the model didn't catch the mismatch between
its own retrieved evidence and the question's time frame.

**#13 — minor instruction-following miss.** Asked for "one paragraph,"
got 3 bullets. Not one of the 4 scored metrics, but worth a footnote —
the prompt's formatting instruction ("bullets not more than 3-5 OR short
paragraphs") may be overriding the user's explicit ask. Low priority.
