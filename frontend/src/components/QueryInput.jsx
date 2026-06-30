import { useState } from "react";

export default function QueryInput({ onSubmit, loading }) {
  const [question, setQuestion] = useState("");

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
    onSubmit(trimmed);
  }

  return (
    <div className="query-input-card">
      <textarea
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
  );
}
