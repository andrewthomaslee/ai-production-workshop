import React, { useEffect, useState } from "react";
import { getJSON, putJSON } from "../api.js";

// The no-code authoring surface: a non-coder writes a skill in plain markdown
// and the agent can immediately use it. No deploy, no restart.
export default function Skills() {
  const [skills, setSkills] = useState([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [body, setBody] = useState("");
  const [status, setStatus] = useState("");

  const refresh = () => getJSON("/api/skills").then((d) => setSkills(d.skills)).catch(() => {});
  useEffect(() => { refresh(); }, []);

  async function load(n) {
    const s = await getJSON(`/api/skills/${n}`);
    setName(s.name); setDescription(s.description); setBody(s.body);
    setStatus("");
  }

  async function save() {
    if (!name.trim()) return setStatus("Name required");
    await putJSON(`/api/skills/${encodeURIComponent(name)}`, { description, body });
    setStatus(`Saved "${name}". The agent can use it now.`);
    refresh();
  }

  function blank() {
    setName(""); setDescription(""); setBody("# When to use\n\n# Steps\n1. \n"); setStatus("");
  }

  return (
    <div className="panel skills">
      <div className="skill-list">
        {skills.map((s) => (
          <button key={s.name} className="skill-chip" onClick={() => load(s.name)} title={s.description}>
            {s.name}
          </button>
        ))}
        <button className="skill-chip new" onClick={blank}>+ new</button>
      </div>
      <div className="editor">
        <input placeholder="skill name (e.g. competitor-research)" value={name} onChange={(e) => setName(e.target.value)} />
        <input placeholder="one-line description (shown to the agent)" value={description} onChange={(e) => setDescription(e.target.value)} />
        <textarea placeholder="Full instructions in markdown…" value={body} onChange={(e) => setBody(e.target.value)} rows={12} />
        <div className="editor-actions">
          <button className="primary" onClick={save}>Save skill</button>
          <span className="status">{status}</span>
        </div>
      </div>
    </div>
  );
}
