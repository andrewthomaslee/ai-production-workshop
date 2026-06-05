// Thin API client. The UI talks ONLY to these endpoints; it imports nothing
// from the Python engine. Same-origin relative URLs work both behind FastAPI
// (prod) and via the Vite dev proxy.

export async function getJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

export async function putJSON(path, body) {
  const r = await fetch(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

// POST and parse JSON defensively. Long requests (e.g. running evals) can be
// interrupted - a server restart (uvicorn --reload on a file save), a dropped
// connection, or a timeout - which leaves an empty/partial body. Rather than
// throwing a cryptic "Unexpected end of JSON input", always resolve to an object
// and surface a readable { error } the UI can show.
export async function postJSON(path, body) {
  let r;
  try {
    r = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    return { error: `Request failed: ${e.message}. Is the backend running?` };
  }
  const text = await r.text();
  if (!text) {
    return {
      error:
        `Empty response (HTTP ${r.status}). The request was interrupted - ` +
        `often the server restarting mid-request (avoid 'uvicorn --reload' while ` +
        `running long tasks like evals), a dropped connection, or a timeout.`,
    };
  }
  try {
    return JSON.parse(text);
  } catch {
    return { error: `Unexpected (non-JSON) response (HTTP ${r.status}): ${text.slice(0, 200)}` };
  }
}

// Open a chat WebSocket. Calls onEvent for each streamed step and onDone with
// the final answer. Returns the socket so the caller can send the request.
export function openChat({ onEvent, onDone, onError }) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "done") onDone(msg.answer);
    else if (msg.type === "error") onError && onError(msg.message);
    else onEvent(msg);
  };
  ws.onerror = () => onError && onError("WebSocket error");
  return ws;
}
