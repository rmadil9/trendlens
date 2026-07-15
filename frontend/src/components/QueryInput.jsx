import { useRef, useState } from "react";

const WINDOWS = [
  { value: "today", label: "Today" },
  { value: "week", label: "This week" },
  { value: "month", label: "This month" },
];

const EXAMPLE_QUERIES = [
  "What's new in AI?",
  "Which startups raised the biggest funding rounds?",
];

export default function QueryInput({ onSubmit, loading, timeWindow, onWindowChange }) {
  const [question, setQuestion] = useState("");
  const textareaRef = useRef(null);

  function handleKeyDown(e) {
    // Enter submits; Shift+Enter adds a newline (natural for a textarea)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const trimmed = question.trim();
    if (!trimmed || loading) return;
    onSubmit(trimmed, timeWindow);
  }

  function handleExampleClick(text) {
    setQuestion(text);
    textareaRef.current?.focus();
  }

  function handleWindowKeyDown(e) {
    const idx = WINDOWS.findIndex((w) => w.value === timeWindow);
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      onWindowChange(WINDOWS[(idx + 1) % WINDOWS.length].value);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      onWindowChange(WINDOWS[(idx - 1 + WINDOWS.length) % WINDOWS.length].value);
    }
  }

  return (
    <div className="ask-section">
      <div className="query-input-card">
        <div
          className="window-selector"
          role="radiogroup"
          aria-label="Time window"
          onKeyDown={handleWindowKeyDown}
        >
          {WINDOWS.map((w) => (
            <button
              key={w.value}
              type="button"
              role="radio"
              aria-checked={timeWindow === w.value}
              tabIndex={timeWindow === w.value ? 0 : -1}
              className={`window-chip${timeWindow === w.value ? " window-chip-active" : ""}`}
              onClick={() => onWindowChange(w.value)}
            >
              {w.label}
            </button>
          ))}
        </div>

        <textarea
          ref={textareaRef}
          className="query-textarea"
          placeholder="Ask about recent news trends…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          disabled={loading}
          aria-label="Your question"
        />

        <div className="query-input-footer">
          <span className="query-hint">Shift + Enter for new line</span>
          <button
            className="query-btn"
            onClick={submit}
            disabled={loading || !question.trim()}
          >
            {loading ? "Searching…" : "Ask TrendLens"}
          </button>
        </div>
      </div>

      <div className="example-chips" aria-label="Example questions">
        {EXAMPLE_QUERIES.map((q) => (
          <button
            key={q}
            type="button"
            className="example-chip"
            onClick={() => handleExampleClick(q)}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
