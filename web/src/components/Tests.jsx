import React, { useState } from "react";
import { postJSON } from "../api.js";

// Agent evals: run the REAL agent on scenarios and grade the result both
// programmatically AND with an LLM judge. Catches behavioral regressions.
export default function Tests() {
  return (
    <div className="panel">
      <p className="panel-hint">
        Catch regressions before your users do. These evals run the real agent on
        each scenario and grade it (programmatically <b>and</b> with an LLM judge).
      </p>
      <Evals />
    </div>
  );
}

function Evals() {
  const [state, setState] = useState({ status: "idle" });
  const run = async () => {
    setState({ status: "running" });
    try {
      const r = await postJSON("/api/evals", {});
      if (r.error) setState({ status: "error", msg: r.error });
      else setState({ status: "done", data: r });
    } catch (e) {
      setState({ status: "error", msg: String(e) });
    }
  };
  const d = state.data;
  return (
    <section className="test-block">
      <div className="test-head">
        <h3>Agent evals <span className="test-sub">real agent · programmatic + LLM judge</span></h3>
        <button className="run-btn evals" onClick={run} disabled={state.status === "running"}>
          {state.status === "running" ? "Running…" : "Run evals"}
        </button>
      </div>
      {state.status === "running" && (
        <div className="empty">Running the real agent on every scenario (~30s). Watch the judge decide…</div>
      )}
      {state.status === "error" && <div className="empty">{state.msg}</div>}
      {d && (
        <>
          <Score passed={d.passed} total={d.total} />
          <div className="cat-row">
            {Object.entries(d.by_category).map(([c, v]) => (
              <span key={c} className={`cat-chip ${v.passed === v.total ? "ok" : "bad"}`}>
                {c} {v.passed}/{v.total}
              </span>
            ))}
          </div>
          {d.results.map((r) => <EvalCard key={r.name} r={r} />)}
        </>
      )}
    </section>
  );
}

function EvalCard({ r }) {
  const [open, setOpen] = useState(!r.passed); // auto-expand failures
  return (
    <div className={`eval-card ${r.passed ? "ok" : "bad"}`}>
      <div className="eval-card-head" onClick={() => setOpen(!open)}>
        <span className="mark">{r.passed ? "✓" : "✗"}</span>
        <code>{r.name}</code>
        <span className="cat-tag">{r.category}</span>
        <span className="eval-dur">{r.duration}s</span>
        <span className="caret">{open ? "▾" : "▸"}</span>
      </div>
      {open && (
        <div className="eval-detail">
          <p className="eval-desc">{r.description}</p>
          {r.checks.map((c, i) => (
            <div key={i} className={`check ${c.passed ? "ok" : "bad"}`}>
              <span className="mark">{c.passed ? "✓" : "✗"}</span>
              <span className={`kind kind-${c.kind}`}>{c.kind === "judge" ? "judge" : "prog"}</span>
              {c.label}
              <div className="check-detail">{c.detail}</div>
            </div>
          ))}
          {r.tools.length > 0 && (
            <div className="eval-tools">tools: {r.tools.map((t, i) => <code key={i}>{t}</code>)}</div>
          )}
        </div>
      )}
    </div>
  );
}

function Score({ passed, total }) {
  const all = passed === total;
  return (
    <div className={`score ${all ? "ok" : "bad"}`}>
      <span className="score-num">{passed}/{total}</span> {all ? "passing" : "passing (regressions!)"}
    </div>
  );
}
