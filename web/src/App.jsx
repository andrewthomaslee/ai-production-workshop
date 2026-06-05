import React, { useEffect, useState } from "react";
import { getJSON } from "./api.js";
import Chat from "./components/Chat.jsx";
import Catalog from "./components/Catalog.jsx";
import Skills from "./components/Skills.jsx";
import Memory from "./components/Memory.jsx";
import Audit from "./components/Audit.jsx";
import Metrics from "./components/Metrics.jsx";
import Tests from "./components/Tests.jsx";
import Files from "./components/Files.jsx";

const TABS = [
  ["capabilities", "🧰 Capabilities"],
  ["files", "📂 Files"],
  ["skills", "📝 Skills"],
  ["memory", "🧠 Memory"],
  ["audit", "🔍 Audit"],
  ["metrics", "📊 Metrics"],
  ["tests", "✅ Tests"],
];

export default function App() {
  const [config, setConfig] = useState(null);
  const [identity, setIdentity] = useState({
    user_id: "demo-user",
    role: "admin",
    model: "gpt-5.4-mini",
    sandbox: "subprocess",
  });
  const [tab, setTab] = useState("capabilities");
  const [bump, setBump] = useState(0); // force side-panel refresh after a chat
  const [openFileReq, setOpenFileReq] = useState(null); // {path, ts} from a chat click

  const openFile = (path) => {
    setOpenFileReq({ path, ts: Date.now() });
    setTab("files");
  };

  useEffect(() => {
    getJSON("/api/config").then(setConfig).catch(() => setConfig({ error: true }));
  }, []);

  const set = (k) => (e) => setIdentity({ ...identity, [k]: e.target.value });

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◆</span>
          <div>
            <h1>Agent Control</h1>
            <p>Production-ready AI · one engine, many users</p>
          </div>
        </div>
        <div className="identity">
          <Field label="User">
            <input value={identity.user_id} onChange={set("user_id")} />
          </Field>
          <Field label="Role" hint="changes what tools the agent can use">
            <select value={identity.role} onChange={set("role")} className={`role role-${identity.role}`}>
              {(config?.roles || ["viewer", "analyst", "admin"]).map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </Field>
          <Field label="Model">
            <select value={identity.model} onChange={set("model")}>
              {(config?.models || ["gpt-5.4-mini"]).map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </Field>
          <Field label="Sandbox">
            <select value={identity.sandbox} onChange={set("sandbox")}>
              {(config?.sandboxes || ["subprocess", "docker"]).map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </Field>
          <span className={`key ${config?.has_key ? "ok" : "bad"}`}>
            {config?.has_key ? "● key set" : "○ no key"}
          </span>
        </div>
      </header>

      <main className="layout">
        <section className="chat-pane">
          <Chat identity={identity} onActivity={() => setBump((b) => b + 1)} onOpenFile={openFile} />
        </section>

        <aside className="side-pane">
          <nav className="tabs">
            {TABS.map(([id, label]) => (
              <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>
                {label}
              </button>
            ))}
          </nav>
          <div className="tab-body">
            {tab === "capabilities" && <Catalog role={identity.role} key={`cap-${identity.role}`} />}
            {tab === "files" && <Files userId={identity.user_id} bump={bump} openReq={openFileReq} />}
            {tab === "skills" && <Skills />}
            {tab === "memory" && <Memory userId={identity.user_id} bump={bump} />}
            {tab === "audit" && <Audit userId={identity.user_id} bump={bump} />}
            {tab === "metrics" && <Metrics bump={bump} />}
            {tab === "tests" && <Tests />}
          </div>
        </aside>
      </main>
    </div>
  );
}

function Field({ label, hint, children }) {
  return (
    <label className="field" title={hint || ""}>
      <span>{label}</span>
      {children}
    </label>
  );
}
