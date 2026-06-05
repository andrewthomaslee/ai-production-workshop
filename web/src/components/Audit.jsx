import React, { useEffect, useState } from "react";
import { getJSON } from "../api.js";

// The audit trail for the current user: every tool call, allowed or denied.
export default function Audit({ userId, bump }) {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    getJSON(`/api/audit?user_id=${encodeURIComponent(userId)}`)
      .then((d) => setRows(d.entries.slice().reverse()))
      .catch(() => setRows([]));
  }, [userId, bump]);

  return (
    <div className="panel">
      <p className="panel-hint">Every tool call by <b>{userId}</b>: the enterprise audit trail.</p>
      {rows.length === 0 ? (
        <div className="empty">No activity yet.</div>
      ) : (
        <table className="audit">
          <thead><tr><th>#</th><th>role</th><th>tool</th><th>status</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.seq} className={r.allowed ? "" : "denied"}>
                <td>{r.seq}</td>
                <td><span className={`role role-${r.role}`}>{r.role}</span></td>
                <td><code>{r.tool}</code></td>
                <td>{r.allowed ? "✓ allowed" : "✗ denied"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
