export default function AnswerPanel({ answer, loading }) {
  if (loading) {
    return (
      <div className="answer-panel" aria-live="polite" aria-busy="true">
        <div className="skeleton-lines">
          <div className="skeleton-line" style={{ width: "90%" }} />
          <div className="skeleton-line" style={{ width: "75%" }} />
          <div className="skeleton-line" style={{ width: "85%" }} />
          <div className="skeleton-line" style={{ width: "60%" }} />
        </div>
      </div>
    );
  }

  if (!answer) return null;

  return (
    // aria-live="polite" tells screen readers to announce when the answer updates
    <div className="answer-panel" aria-live="polite">
      <h2 className="panel-label">Answer</h2>
      {/* white-space: pre-wrap in CSS preserves newlines in the GPT response */}
      <p className="answer-text">{answer}</p>
    </div>
  );
}
