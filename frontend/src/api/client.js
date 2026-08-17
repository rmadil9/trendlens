// Relative, not absolute — and deliberately not a build-time env var.
//
// Frontend code runs in the visitor's browser, so the old "http://localhost:8000"
// meant *their* machine, not the server. Same-origin deployment removes the
// problem rather than parameterising it: nginx serves this bundle and proxies
// /api to the backend on the same host, so there is nothing environment-specific
// left to configure. Vite's dev server proxies the same path (see vite.config.js).
const BASE_URL = "/api";

// All API calls live here — components call these functions, never fetch() directly.

export async function postQuery(question, timeWindow = "today") {
  const response = await fetch(`${BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, time_window: timeWindow }),
  });

  // response.ok is true for 2xx status codes.
  // We throw here so the caller (App.jsx) can catch it in one place
  // rather than every component checking response.ok itself.
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail ?? `Server error: ${response.status}`);
  }

  return response.json(); // { answer: string, sources: Source[] }
}

export async function getHealth() {
  const response = await fetch(`${BASE_URL}/health`);
  if (!response.ok) throw new Error("Backend unreachable");
  return response.json();
}
