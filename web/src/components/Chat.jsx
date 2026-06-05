import React, { useRef, useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { openChat, getJSON } from "../api.js";

// Render the agent's answer as markdown (it returns bold, lists, tables, code).
// react-markdown is XSS-safe by default (no raw HTML). Links open in a new tab.
// If an inline `code` token names a file in the workspace, make it clickable so
// it opens in the Files tab.
function Markdown({ text, fileMap, onOpenFile }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: (props) => <a target="_blank" rel="noopener noreferrer" {...props} />,
          code: ({ children, className, ...props }) => {
            const raw = String(children);
            const hit = !className && !raw.includes("\n") && fileMap && fileMap.get(raw.trim());
            if (hit && onOpenFile) {
              return (
                <code className="file-link" title="Open file" onClick={() => onOpenFile(hit)}>
                  {children}
                </code>
              );
            }
            return <code className={className} {...props}>{children}</code>;
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}

const TOOL_ICON = {
  run_python: "🐍", install_packages: "📦", read_file: "📄", write_file: "✏️",
  list_files: "📁", remember: "🧠", load_skill: "📝", web_search: "🔎",
  web_fetch: "🌐", start_training: "🏋️", training_status: "📈", deploy_site: "🚀",
};

const SUGGESTIONS = [
  "Create sales.csv with 5 rows, then chart total revenue per product",
  "Research Anthropic and write a competitor brief to brief.md",
  "Train a model 'churn' with learning_rate 5.0; if it fails, fix it",
  "Build and deploy a landing page for a coffee brand 'Brewly'",
];

export default function Chat({ identity, onActivity, onOpenFile }) {
  const [turns, setTurns] = useState([]); // {role, text} or {role:'steps', steps:[]}
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [fileMap, setFileMap] = useState(new Map()); // filename/path -> path
  const scroller = useRef(null);

  useEffect(() => {
    if (scroller.current) scroller.current.scrollTop = scroller.current.scrollHeight;
  }, [turns, busy]);

  // Keep a lookup of the user's workspace files so we can linkify filenames the
  // agent mentions. Refresh on user switch and after each answer (new files).
  const loadFiles = () =>
    getJSON(`/api/files?user_id=${encodeURIComponent(identity.user_id)}`)
      .then((d) => {
        const m = new Map();
        for (const f of d.files) {
          m.set(f.path, f.path);
          m.set(f.path.split("/").pop(), f.path); // basename too
        }
        setFileMap(m);
      })
      .catch(() => setFileMap(new Map()));

  useEffect(() => { loadFiles(); }, [identity.user_id]);

  function send(text) {
    const message = (text ?? input).trim();
    if (!message || busy) return;
    setInput("");
    setBusy(true);
    setTurns((t) => [...t, { role: "user", text: message }, { role: "steps", steps: [] }]);

    const pushStep = (step) =>
      setTurns((t) => {
        const copy = [...t];
        const last = copy[copy.length - 1];
        if (last && last.role === "steps") last.steps = [...last.steps, step];
        return copy;
      });

    const ws = openChat({
      onEvent: (msg) => {
        if (msg.type === "tool") pushStep({ kind: "tool", name: msg.name, input: msg.input });
        else if (msg.type === "result") pushStep({ kind: "result", output: msg.output });
        else if (msg.type === "thinking") pushStep({ kind: "thinking", text: msg.text });
      },
      onDone: (answer) => {
        setTurns((t) => [...t, { role: "agent", text: answer }]);
        setBusy(false);
        onActivity && onActivity();
        loadFiles(); // the agent may have created/edited files
        ws.close();
      },
      onError: (err) => {
        setTurns((t) => [...t, { role: "agent", text: "⚠️ " + err }]);
        setBusy(false);
        ws.close();
      },
    });
    ws.onopen = () => ws.send(JSON.stringify({ ...identity, message }));
  }

  return (
    <div className="chat">
      <div className="messages" ref={scroller}>
        {turns.length === 0 && (
          <div className="welcome">
            <h2>👋 Drive the agent</h2>
            <p>Watch it work step by step. Try switching <b>Role</b> to <code>viewer</code> and ask it to run code to see permissions in action.</p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {turns.map((turn, i) => {
          if (turn.role === "user") return <div key={i} className="msg user"><div className="bubble">{turn.text}</div></div>;
          if (turn.role === "agent") return <div key={i} className="msg agent"><div className="bubble"><Markdown text={turn.text} fileMap={fileMap} onOpenFile={onOpenFile} /></div></div>;
          return <Steps key={i} steps={turn.steps} live={busy && i === turns.length - 1} />;
        })}
      </div>

      <form className="composer" onSubmit={(e) => { e.preventDefault(); send(); }}>
        <input
          placeholder={busy ? "Agent is working…" : "Ask the agent to do something…"}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()}>{busy ? "…" : "Run"}</button>
      </form>
    </div>
  );
}

function Steps({ steps, live }) {
  if (steps.length === 0 && !live) return null;
  return (
    <div className="steps">
      {steps.map((s, i) => {
        if (s.kind === "tool")
          return (
            <div key={i} className="step tool">
              <span className="icon">{TOOL_ICON[s.name] || "⚙️"}</span>
              <code>{s.name}</code>
              <span className="args">{summarize(s.input)}</span>
            </div>
          );
        if (s.kind === "result")
          return <div key={i} className="step result"><pre>{clip(s.output, 500)}</pre></div>;
        return <div key={i} className="step thinking">{clip(s.text, 280)}</div>;
      })}
      {live && <div className="step pulse">● working…</div>}
    </div>
  );
}

const clip = (s, n) => (s && s.length > n ? s.slice(0, n) + "…" : s || "");
const summarize = (obj) => {
  try { const s = JSON.stringify(obj); return s.length > 80 ? s.slice(0, 80) + "…" : s; }
  catch { return ""; }
};
