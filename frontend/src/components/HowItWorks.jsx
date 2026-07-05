function FeedIcon() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <circle cx="6" cy="18" r="1.6" fill="currentColor" stroke="none" />
      <path d="M5 12a7 7 0 0 1 7 7" />
      <path d="M5 6a13 13 0 0 1 13 13" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <circle cx="10.5" cy="10.5" r="6.5" />
      <line x1="15.2" y1="15.2" x2="20.5" y2="20.5" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 5.5h16v10H9l-4.2 3.8V15.5H4z" />
    </svg>
  );
}

const STEPS = [
  {
    title: "Ingest",
    text: "Tech news from multiple RSS sources is fetched, cleaned, and embedded on a schedule.",
    Icon: FeedIcon,
  },
  {
    title: "Retrieve",
    text: "Your question is matched against recent articles, filtered by the time window you pick.",
    Icon: SearchIcon,
  },
  {
    title: "Answer",
    text: "GPT-4o-mini synthesizes a response grounded in those articles, with citations.",
    Icon: ChatIcon,
  },
];

export default function HowItWorks() {
  return (
    <section className="how-it-works" id="how-it-works">
      <div className="section-inner">
        <h2 className="section-heading">How it works</h2>
        <div className="steps-row">
          {STEPS.map((step, i) => (
            <div className="step-card" key={step.title}>
              <div className="step-icon">
                <step.Icon />
              </div>
              <h3 className="step-title">
                <span className="step-number">{i + 1}</span> {step.title}
              </h3>
              <p className="step-text">{step.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
