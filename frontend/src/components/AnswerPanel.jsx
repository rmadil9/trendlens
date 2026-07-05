import { formatAnswer } from "../utils/formatAnswer";

const WINDOW_LABELS = { today: "Today", week: "This week", month: "This month" };

export default function AnswerPanel({ answer, loading, timeWindow }) {
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
    <div className="answer-panel answer-panel-in" aria-live="polite">
      <div className="answer-header">
        <h2 className="panel-label">Answer</h2>
        {timeWindow && (
          <span className="window-tag">{WINDOW_LABELS[timeWindow] ?? timeWindow}</span>
        )}
      </div>
      <div className="answer-text">{formatAnswer(answer)}</div>
    </div>
  );
}
