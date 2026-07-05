const BASE_URL = "http://localhost:8000";

// All API calls live here — components call these functions, never fetch() directly.
// This means if the base URL changes (e.g. prod), you change it in one place.

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
