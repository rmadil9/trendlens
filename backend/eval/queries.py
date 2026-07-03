"""
The 15 test queries — single source of truth for the eval set.

eval/test_queries.md documents the *why* behind each one; this file is
what run_eval.py actually executes. Keep them in sync by hand if you add
a query — 15 rows isn't worth generating one file from the other.
"""

QUERIES = [
    # 1. Basic retrieval — clear, on-topic, should have obvious matches
    {"id": 1, "category": "Basic retrieval",
     "question": "What's new with Anthropic and Claude?"},
    {"id": 2, "category": "Basic retrieval",
     "question": "What's happening with Sony and PlayStation physical game discs?"},
    {"id": 3, "category": "Basic retrieval",
     "question": "What AI startups raised funding recently?"},

    # 2. Time-weighting — same topic, different time phrasing
    {"id": 4, "category": "Time-weighting",
     "question": "What happened in AI today?"},
    {"id": 5, "category": "Time-weighting",
     "question": "What happened in AI this week?"},
    {"id": 6, "category": "Time-weighting",
     "question": "What's the recent AI news?",
     "note": "Should return IDENTICAL results to #4 — 'recent' is a synonym "
              "for 'today' in parse_time_window(). Diverging results = regression."},

    # 3. Specificity — narrow/named-entity vs. one deliberately broad query
    {"id": 7, "category": "Specificity",
     "question": "What did Anthropic say about Alibaba's Claude cloning attack?"},
    {"id": 8, "category": "Specificity",
     "question": "Tell me about Sony's disc production shutdown timeline"},
    {"id": 9, "category": "Specificity",
     "question": "What's new in tech this week?",
     "note": "Deliberately broad/generic — stress-tests whether synthesis "
              "stays coherent instead of turning into a grab-bag."},

    # 4. Edge cases — designed to probe known weak points, not to "pass"
    {"id": 10, "category": "Edge case",
     "question": "What happened in AI last year?",
     "note": "Expected to FAIL correctly: parse_time_window() has no 'last "
              "year' branch, so this silently falls back to the 30-day "
              "default instead of actually filtering to last year."},
    {"id": 11, "category": "Edge case",
     "question": "What did NVIDIA announce this week?",
     "note": "NVIDIA never appears in the corpus. retrieve() has no "
              "similarity threshold, so Qdrant still returns top-5 "
              "unrelated chunks. Tests whether generation refuses instead "
              "of hallucinating around them."},
    {"id": 12, "category": "Edge case",
     "question": "What's the weather forecast for next week?",
     "note": "Fully off-topic — same guardrail test, different angle."},

    # 5. Answer quality / synthesis — must merge facts from 2+ articles
    {"id": 13, "category": "Answer quality",
     "question": "Summarize this week's Anthropic news in one paragraph"},
    {"id": 14, "category": "Answer quality",
     "question": "Walk me through Sony's PlayStation disc discontinuation story"},
    {"id": 15, "category": "Answer quality",
     "question": "What AI funding rounds happened this week and how much did each raise?"},
]
