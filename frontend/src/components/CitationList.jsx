export default function CitationList({ sources }) {
  if (!sources.length) return null;

  return (
    <div className="citation-list">
      <h2 className="panel-label">Sources</h2>
      <ol className="citations">
        {sources.map((s, i) => (
          <li key={s.url} className="citation-item">
            <span className="citation-index">{i + 1}</span>
            <div className="citation-body">
              <a
                href={s.url}
                target="_blank"          // open in new tab
                rel="noopener noreferrer" // security: prevents new tab from accessing window.opener
                className="citation-title"
              >
                {s.title}
              </a>
              <div className="citation-meta">
                <span className="citation-source">{s.source}</span>
                <span className="citation-sep">·</span>
                {/* published_at is a Unix timestamp (seconds), JS Date expects milliseconds */}
                <span className="citation-date">
                  {new Date(s.published_at * 1000).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </span>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
