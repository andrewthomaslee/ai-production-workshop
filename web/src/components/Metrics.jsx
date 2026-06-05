import React, { useEffect, useState } from "react";
import { getJSON } from "../api.js";

export default function Metrics({ bump }) {
  const [m, setM] = useState(null);
  useEffect(() => {
    getJSON("/api/metrics").then(setM).catch(() => setM(null));
  }, [bump]);

  if (!m) return <div className="panel"><div className="empty">No metrics yet.</div></div>;
  return (
    <div className="panel">
      <p className="panel-hint">Live service metrics (also at <code>GET /api/metrics</code>).</p>
      <div className="metric-grid">
        <Stat label="Requests" value={m.requests} />
        <Stat label="Errors" value={m.errors} />
        <Stat label="Avg latency" value={`${m.avg_seconds}s`} />
        <Stat label="Models used" value={Object.keys(m.by_model || {}).length} />
      </div>
      <div className="by-model">
        {Object.entries(m.by_model || {}).map(([model, n]) => (
          <div key={model} className="bm-row"><code>{model}</code><span>{n}</span></div>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
