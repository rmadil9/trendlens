# How to Score an Eval Run

Run `.venv/bin/python -m eval.run_eval` from `backend/`, open the newest
file in `eval/results/`, and score each of the 15 queries against the
4 metrics below. Fill `eval/results/scoresheet.md` (copy the template at
the bottom of this file) as you go.

## Precision@5

For each of the 5 retrieved chunks, ask: **"Would this chunk actually
help answer the question?"** Mark each ✓ or ✗ using the chunk preview
text shown in the dump. Score = (# ✓) / 5.

- ✓ — on-topic, plausibly supports part of the answer
- ✗ — off-topic, or same broad topic but wrong specific subject (e.g. an
  Anthropic-safety chunk retrieved for a Sony-disc question)

**Exception:** for the edge-case queries (#10–12), low precision is the
*expected, correct* outcome — don't mark the query "failed" for that.
Note it instead ("0/5, as expected — no NVIDIA content exists").

## Time-filter correctness

Compare each retrieved chunk's date (printed in the dump) against the
window implied by the query's time phrase:

| Phrase | Expected window |
|---|---|
| "today" / "recent" | last ~24h |
| "this week" | last ~7 days |
| unspecified / "this month" | last ~30 days |
| "last year" (query #10) | should be ~1 year, but isn't — known bug |

Mark **PASS** if every returned chunk's date falls inside the expected
window, **FAIL** otherwise. Query #10 is *expected* to FAIL — that's the
bug it's designed to surface, not a scoring mistake.

## Faithfulness

Read the generated answer sentence by sentence. For each factual claim,
search the retrieved chunks' preview text for support.

- **PASS** — every claim traces back to something in the retrieved chunks
- **FAIL** — quote the exact unsupported sentence in your notes. This is
  the actual hallucination check — the one that matters most.

For the off-topic edge cases (#11, #12): **PASS** means the model said
something like *"I could not find relevant information..."* rather than
inventing an answer out of the irrelevant chunks it was handed.

## Citation accuracy

For each inline `[Source, Date]` tag in the answer:

1. Does that Source + Date actually match one of the retrieved chunks
   listed in the dump?
2. Is it attached to a claim that specific chunk actually supports —
   not just "this source exists somewhere in the context"?

Score = (# correct citations) / (# citations made). If the model made
**zero** citations despite being instructed to, note that separately —
it's an instruction-following failure, not "N/A."

---

## Scoresheet template

Copy this into `eval/results/scoresheet.md` and fill one row per query.

```markdown
| # | Category | Precision@5 | Time-filter | Faithfulness | Citations | Notes |
|---|---|---|---|---|---|---|
| 1 | Basic retrieval | /5 | Pass/Fail | Pass/Fail | / | |
| 2 | Basic retrieval | /5 | Pass/Fail | Pass/Fail | / | |
| 3 | Basic retrieval | /5 | Pass/Fail | Pass/Fail | / | |
| 4 | Time-weighting | /5 | Pass/Fail | Pass/Fail | / | |
| 5 | Time-weighting | /5 | Pass/Fail | Pass/Fail | / | |
| 6 | Time-weighting | /5 | Pass/Fail | Pass/Fail | / | should match #4 |
| 7 | Specificity | /5 | Pass/Fail | Pass/Fail | / | |
| 8 | Specificity | /5 | Pass/Fail | Pass/Fail | / | |
| 9 | Specificity | /5 | Pass/Fail | Pass/Fail | / | |
| 10 | Edge case | /5 | Pass/Fail | Pass/Fail | / | expect Time-filter FAIL |
| 11 | Edge case | /5 | Pass/Fail | Pass/Fail | / | expect low precision, PASS faithfulness |
| 12 | Edge case | /5 | Pass/Fail | Pass/Fail | / | expect low precision, PASS faithfulness |
| 13 | Answer quality | /5 | Pass/Fail | Pass/Fail | / | |
| 14 | Answer quality | /5 | Pass/Fail | Pass/Fail | / | |
| 15 | Answer quality | /5 | Pass/Fail | Pass/Fail | / | |
```

Once filled, roll it up into the README table:
- **Precision@5** = average of all 15 (or exclude edge cases if you want
  a cleaner "does retrieval work" number — say which you did)
- **Time-filter Accuracy** = PASS count / 15
- **Answer Faithfulness** = PASS count / 15
- **Citation Accuracy** = sum(correct) / sum(total citations made)
