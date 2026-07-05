// Splits on **bold** and [Source, date]-style citations, keeping the
// separators so we can re-render each piece as the right element.
const INLINE_TOKEN = /(\*\*[^*]+\*\*|\[[^\]]+\])/g;

function renderInline(text) {
  return text.split(INLINE_TOKEN).filter(Boolean).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("[") && part.endsWith("]")) {
      return (
        <span className="citation-badge" key={i}>
          {part.slice(1, -1)}
        </span>
      );
    }
    return part;
  });
}

// Turns the API's markdown-ish answer text into JSX: bullet lines become a
// styled <ul>, everything else becomes a paragraph, with **bold** and
// [Source, date] citations rendered inline within either.
export function formatAnswer(text) {
  const lines = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  const blocks = [];
  for (const line of lines) {
    const bulletMatch = line.match(/^[-*]\s+(.*)/);
    if (bulletMatch) {
      const last = blocks[blocks.length - 1];
      if (last && last.type === "list") {
        last.items.push(bulletMatch[1]);
      } else {
        blocks.push({ type: "list", items: [bulletMatch[1]] });
      }
    } else {
      blocks.push({ type: "para", text: line });
    }
  }

  return blocks.map((block, i) => {
    if (block.type === "list") {
      return (
        <ul className="answer-list" key={i}>
          {block.items.map((item, j) => (
            <li key={j}>{renderInline(item)}</li>
          ))}
        </ul>
      );
    }
    return (
      <p className="answer-para" key={i}>
        {renderInline(block.text)}
      </p>
    );
  });
}
