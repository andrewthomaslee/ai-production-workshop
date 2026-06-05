import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getJSON } from "../api.js";

const ICON = { text: "📄", image: "🖼️", binary: "📦" };

// Browse the current user's workspace and open files. `openReq` ({path, ts}) lets
// a click on a filename in a chat message jump straight to that file.
export default function Files({ userId, bump, openReq }) {
  const [files, setFiles] = useState([]);
  const [sel, setSel] = useState(null);
  const [content, setContent] = useState("");

  const rawUrl = (path) =>
    `/api/files/raw?user_id=${encodeURIComponent(userId)}&path=${encodeURIComponent(path)}`;
  // Path-based URL so an HTML file's relative links resolve (for iframe / new tab).
  const serveUrl = (path) =>
    `/api/files/serve/${encodeURIComponent(userId)}/${path.split("/").map(encodeURIComponent).join("/")}`;
  const isHtml = (path) => /\.html?$/i.test(path);

  useEffect(() => {
    getJSON(`/api/files?user_id=${encodeURIComponent(userId)}`)
      .then((d) => setFiles(d.files))
      .catch(() => setFiles([]));
  }, [userId, bump]);

  const open = (f) => {
    setSel(f);
    if (f.kind === "image" || f.kind === "binary" || isHtml(f.path)) return setContent("");
    fetch(rawUrl(f.path))
      .then((r) => r.text())
      .then(setContent)
      .catch(() => setContent("(could not load file)"));
  };

  // Honor an open request coming from a chat-message file link.
  useEffect(() => {
    if (!openReq || !openReq.path) return;
    const f = files.find((x) => x.path === openReq.path) || { path: openReq.path, kind: guessKind(openReq.path) };
    open(f);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openReq, files]);

  return (
    <div className="panel">
      <p className="panel-hint">
        Files in <b>{userId}</b>'s workspace. Click to open. This is the sandboxed
        directory the agent reads and writes (per user, isolated).
      </p>
      {files.length === 0 ? (
        <div className="empty">No files yet. Ask the agent to create one.</div>
      ) : (
        <div className="files">
          <ul className="file-list">
            {files.map((f) => (
              <li key={f.path} className={sel?.path === f.path ? "active" : ""} onClick={() => open(f)}>
                <span className="fi">{ICON[f.kind] || "📄"}</span>
                <code>{f.path}</code>
                <span className="fsize">{fmtSize(f.size)}</span>
              </li>
            ))}
          </ul>

          {sel && (
            <div className="file-view">
              <div className="file-view-head">
                <code>{sel.path}</code>
                <a
                  href={isHtml(sel.path) ? serveUrl(sel.path) : rawUrl(sel.path)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="dl"
                >
                  {isHtml(sel.path) ? "open in new tab ↗" : "open raw ↗"}
                </a>
              </div>
              {sel.kind === "image" ? (
                <img src={rawUrl(sel.path)} alt={sel.path} />
              ) : sel.kind === "binary" ? (
                <div className="empty">Binary file. Use “open raw” to download.</div>
              ) : isHtml(sel.path) ? (
                <iframe
                  className="html-frame"
                  title={sel.path}
                  src={serveUrl(sel.path)}
                  sandbox="allow-scripts allow-popups allow-forms"
                />
              ) : sel.path.endsWith(".md") ? (
                <div className="md"><ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown></div>
              ) : (
                <pre className="file-code">{content}</pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function fmtSize(n) {
  return n < 1024 ? `${n} B` : `${(n / 1024).toFixed(1)} KB`;
}
function guessKind(path) {
  const ext = path.slice(path.lastIndexOf(".")).toLowerCase();
  return [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"].includes(ext) ? "image" : "text";
}
