import { useRef, useState } from "react";
import { postQuery } from "./api/client";
import Logo from "./components/Logo";
import QueryInput from "./components/QueryInput";
import AnswerPanel from "./components/AnswerPanel";
import CitationList from "./components/CitationList";
import HowItWorks from "./components/HowItWorks";
import Architecture from "./components/Architecture";
import Footer from "./components/Footer";
import "./App.css";

export default function App() {
  // All state lives here — child components only receive what they need to render.
  // This is the "single source of truth" pattern: one place to read & update state.
  const [answer, setAnswer] = useState(null);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [timeWindow, setTimeWindow] = useState("today");
  const [usedWindow, setUsedWindow] = useState("today");
  const [lastQuestion, setLastQuestion] = useState(null);
  const resultsRef = useRef(null);

  async function handleQuery(question, window) {
    setLastQuestion(question);
    setUsedWindow(window);
    setLoading(true);
    setError(null);
    setAnswer(null);
    setSources([]);

    // Results section mounts as soon as loading starts — scroll it into view
    // once the browser has painted it.
    requestAnimationFrame(() => {
      resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    try {
      const data = await postQuery(question, window);
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

  function handleRetry() {
    if (lastQuestion) handleQuery(lastQuestion, usedWindow);
  }

  const hasResults = answer || loading || error;

  return (
    <div className="app">
      <section className="hero">
        <div className="hero-glow" aria-hidden="true" />
        <div className="hero-inner">
          <div className="brand">
            <Logo />
            <span className="brand-name">TrendLens</span>
          </div>
          <h1 className="hero-headline">Ask what's happening in tech, right now.</h1>
          <p className="hero-subtext">
            Ask questions about what's happening in tech news — get synthesized, source-cited answers.
          </p>

          <QueryInput
            onSubmit={handleQuery}
            loading={loading}
            timeWindow={timeWindow}
            onWindowChange={setTimeWindow}
          />
        </div>
      </section>

      {hasResults && (
        <section className="results-section" ref={resultsRef}>
          <div className="results-inner">
            {error && (
              <div className="error-banner" role="alert">
                <span className="error-icon">⚠</span>
                <span className="error-text">{error}</span>
                <button type="button" className="retry-btn" onClick={handleRetry}>
                  Retry
                </button>
              </div>
            )}

            {!error && (answer || loading) && (
              <AnswerPanel answer={answer} loading={loading} timeWindow={usedWindow} />
            )}

            {!error && sources.length > 0 && !loading && <CitationList sources={sources} />}
          </div>
        </section>
      )}

      <HowItWorks />
      <Architecture />
      <Footer />
    </div>
  );
}
