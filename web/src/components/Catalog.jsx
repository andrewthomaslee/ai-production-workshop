import React, { useEffect, useState } from "react";
import { getJSON } from "../api.js";

// Shows every tool and whether the CURRENT role may use it. Flip the Role
// selector in the header and watch the green/locked states change live; this
// is RBAC made visible.
export default function Catalog({ role }) {
  const [tools, setTools] = useState([]);
  useEffect(() => {
    getJSON(`/api/tools?role=${role}`).then((d) => setTools(d.tools)).catch(() => setTools([]));
  }, [role]);

  return (
    <div className="panel">
      <p className="panel-hint">
        Tools available to role <b className={`role role-${role}`}>{role}</b>. Locked tools are
        hidden from the agent and refused if called.
      </p>
      <ul className="tool-list">
        {tools.map((t) => (
          <li key={t.name} className={t.allowed_for_role ? "allowed" : "locked"}>
            <div className="tool-head">
              <span className="state">{t.allowed_for_role ? "✓" : "🔒"}</span>
              <code>{t.name}</code>
              <span className={`badge role-${t.min_role}`}>{t.min_role}+</span>
            </div>
            <p>{t.description}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
