import { useState } from "react";
import { postQuery } from "./api/client";
import QueryInput from "./components/QueryInput";
import AnswerPanel from "./components/AnswerPanel";
import CitationList from "./components/CitationList";
import "./App.css";

export default function App() {
  // All state lives here — child components only receive what they need to render.
  // This is the "single source of truth" pattern: one place to read & update state.
  const [answer, setAnswer] = useState(null);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleQuery(question) {
    setLoading(true);
    setError(null);
    setAnswer(null);
    setSources([]);

    try {
      const data = await postQuery(question);
      setAnswer(data.answer);
      setSources(data.sources);
    } catch (err) {
      // Two cases: (1) network error (backend down) → TypeError with no .message
      //            (2) our API threw an HTTPException → err.message is the detail string
      setError(err.message || "Could not reach the backend. Is the server running?");
    } finally {
      // finally always runs — clears loading whether we succeeded or failed
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-inner">
          <h1 className="app-logo">TrendLens</h1>
          <p className="app-tagline">Ask questions about what's happening in the news</p>
        </div>
      </header>

      <main className="app-main">
        <QueryInput onSubmit={handleQuery} loading={loading} />

        {error && (
          <div className="error-banner" role="alert">
            <span className="error-icon">⚠</span>
            {error}
          </div>
        )}

        {/* Show answer + citations only after a successful response */}
        {(answer || loading) && (
          <AnswerPanel answer={answer} loading={loading} />
        )}

        {sources.length > 0 && !loading && (
          <CitationList sources={sources} />
        )}

        {/* Empty state — shown before the first query */}
        {!answer && !loading && !error && (
          <div className="empty-state">
            <p>Try: <em>"What's new in AI this week?"</em> or <em>"Latest developments in climate tech"</em></p>
          </div>
        )}
      </main>
    </div>
  );
}
