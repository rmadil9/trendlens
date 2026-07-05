const ARCH_POINTS = [
  { label: "Backend", text: "FastAPI (Python), async, serves the query API." },
  { label: "Vector store", text: "Qdrant with native metadata filtering for time-weighted retrieval." },
  { label: "Embeddings", text: "OpenAI text-embedding-3-small; swappable via config." },
  { label: "Generation", text: "GPT-4o-mini with source-citation prompting." },
  { label: "Metadata & dedup", text: "SQLite tracks articles and ingestion state." },
  { label: "Scheduling", text: "APScheduler polls RSS feeds; event-driven ingestion (RabbitMQ) is planned." },
];

export default function Architecture() {
  return (
    <section className="architecture" id="architecture">
      <div className="section-inner">
        <h2 className="section-heading">Architecture</h2>
        <div className="arch-grid">
          {ARCH_POINTS.map((p) => (
            <div className="arch-row" key={p.label}>
              <span className="arch-label">{p.label}</span>
              <span className="arch-text">{p.text}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
