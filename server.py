"""HTTP + WebSocket API: the production surface over the same agent engine.

This file turns the single-user CLI engine into a multi-tenant service:
  - a `SessionStore` gives each user their own isolated Session
  - a `Policy` + `AuditLog` enforce and record permissions
  - a WebSocket streams the loop's events (thinking / tool / result) live so a UI
    can show the agent working, step by step

Crucially, it IMPORTS the engine (agent/*) and adds nothing to it; the loop,
tools, skills, memory, and sandbox are unchanged. The API is a surface, not a
rewrite. The React client (web/) talks only to these endpoints.

Run:  uv run uvicorn server:app --port 8000
      (avoid --reload while running long tasks like evals: saving a file restarts
       the server mid-request and the client sees an empty/aborted response.)
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel

from agent.core.audit import AuditLog
from agent.core.observability import Metrics, log_event
from agent.core.policy import ROLE_TOOLS, ROLES, Policy
from agent.core.session import SessionStore
from agent.skills import SkillLibrary

load_dotenv()

ROOT = Path(__file__).parent
MODELS = ["gpt-5.4-mini", "gpt-5.5", "gpt-5.4-nano"]
SANDBOXES = ["subprocess", "docker"]
DEFAULT_MODEL = "gpt-5.4-mini"

# --- shared, app-level singletons -------------------------------------------
skills = SkillLibrary(ROOT / "agent" / "skills")
policy = Policy()
audit = AuditLog(ROOT / "data" / "audit.jsonl")
metrics = Metrics()
# Bound each model call so one hung request can't stall a whole eval run (which
# would otherwise hold the HTTP response open until something upstream times out
# and the client sees an empty body).
client = OpenAI(timeout=90.0, max_retries=2) if os.environ.get("OPENAI_API_KEY", "").startswith("sk-") else None
store = SessionStore(root=ROOT, skills=skills, client=client, policy=policy, audit=audit)

app = FastAPI(title="Workshop Agent API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


def _min_role(tool: str) -> str:
    for role in ROLES:  # ordered viewer -> analyst -> admin
        if tool in ROLE_TOOLS[role]:
            return role
    return "admin"


# --- request models ----------------------------------------------------------
class ChatRequest(BaseModel):
    user_id: str = "guest"
    role: str = "admin"
    model: str = DEFAULT_MODEL
    sandbox: str = "subprocess"
    message: str


class SkillBody(BaseModel):
    description: str
    body: str


# --- basic / config ----------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"ok": True, "has_key": client is not None}


@app.get("/api/config")
def config():
    return {
        "models": MODELS,
        "default_model": DEFAULT_MODEL,
        "sandboxes": SANDBOXES,
        "roles": ROLES,
        "has_key": client is not None,
    }


@app.get("/api/tools")
def tools(role: str = "admin"):
    """The full tool catalog with the minimum role each requires, and whether the
    given role may use it. Powers the client's capability view."""
    allowed = ROLE_TOOLS.get(role, set())
    # Build one throwaway session-less view from any user's registry shape.
    catalog = []
    sample = store.get("__catalog__", "admin", DEFAULT_MODEL, "subprocess")
    for name, tool in sorted(sample.registry.tools.items()):
        catalog.append({
            "name": name,
            "description": tool.description,
            "min_role": _min_role(name),
            "allowed_for_role": name in allowed,
        })
    return {"role": role, "tools": catalog}


# --- skills (no-code authoring) ---------------------------------------------
@app.get("/api/skills")
def list_skills():
    return {"skills": [{"name": n, "description": d} for n, d in skills.catalog()]}


@app.get("/api/skills/{name}")
def get_skill(name: str):
    body = skills.body(name)
    if body is None:
        return JSONResponse({"error": f"no skill '{name}'"}, status_code=404)
    desc = dict(skills.catalog()).get(name, "")
    return {"name": name, "description": desc, "body": body}


@app.put("/api/skills/{name}")
def save_skill(name: str, payload: SkillBody):
    skills.save(name, payload.description, payload.body)
    return {"ok": True, "name": name}


# --- per-user state inspection ----------------------------------------------
@app.get("/api/memory")
def get_memory(user_id: str = "guest"):
    session = store.get(user_id, "admin", DEFAULT_MODEL, "subprocess")
    return {"user_id": user_id, "memory": session.memory.read()}


# --- workspace files (browse + open) ----------------------------------------
DATA_ROOT = (ROOT / "data").resolve()
_TEXT_EXT = {".txt", ".md", ".py", ".csv", ".tsv", ".json", ".jsonl", ".html",
             ".css", ".js", ".yaml", ".yml", ".xml", ".log", ".sh", ".ini"}
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}


def _user_workspace(user_id: str) -> Path | None:
    """The user's workspace dir, with a guard so a crafted user_id can't escape data/."""
    ws = (ROOT / "data" / user_id / "workspace").resolve()
    return ws if ws.is_relative_to(DATA_ROOT) else None


@app.get("/api/files")
def list_workspace_files(user_id: str = "guest"):
    """List files in the user's workspace (the dir the agent reads and writes)."""
    ws = _user_workspace(user_id)
    files = []
    if ws and ws.exists():
        for p in sorted(ws.rglob("*")):
            if p.is_file():
                ext = p.suffix.lower()
                kind = "image" if ext in _IMAGE_EXT else "text" if ext in _TEXT_EXT else "binary"
                files.append({"path": str(p.relative_to(ws)), "size": p.stat().st_size, "kind": kind})
    return {"user_id": user_id, "files": files}


@app.get("/api/files/raw")
def get_workspace_file(user_id: str = "guest", path: str = ""):
    """Serve one workspace file (text or image), scoped to the user's workspace."""
    ws = _user_workspace(user_id)
    if ws is None:
        return JSONResponse({"error": "invalid user"}, status_code=400)
    target = (ws / path).resolve()
    if not target.is_relative_to(ws) or not target.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(str(target))


@app.get("/api/files/serve/{user_id}/{path:path}")
def serve_workspace_file(user_id: str, path: str):
    """Serve a workspace file at a real URL PATH (not a query string), so an HTML
    file's relative links (./style.css, images) resolve and it renders correctly
    in an iframe preview or a new tab. Same workspace scoping as /api/files/raw."""
    ws = _user_workspace(user_id)
    if ws is None:
        return JSONResponse({"error": "invalid user"}, status_code=400)
    target = (ws / path).resolve()
    if not target.is_relative_to(ws) or not target.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(str(target))


@app.get("/api/audit")
def get_audit(user_id: str | None = None):
    return {"entries": audit.entries(user_id)}


@app.get("/api/metrics")
def get_metrics():
    return metrics.snapshot()


# --- testing: deterministic boundary suite + behavioral agent evals ----------
@app.post("/api/tests")
def run_boundary_tests():
    """Deterministic boundary suite (no LLM): the mechanical guarantees."""
    from scripts.test_suite import run as run_suite
    return run_suite()


@app.get("/api/evals")
def list_evals():
    """The eval scenarios and their checks, without running them."""
    from agent.evals.run import list_cases
    return {"cases": list_cases()}


@app.post("/api/evals")
def run_evals_endpoint():
    """Run the real agent on every scenario and grade it (programmatic + judge).
    This is a normal (sync) endpoint, so FastAPI runs it in a worker thread and
    the event loop stays responsive while the agent works."""
    if client is None:
        return JSONResponse({"error": "OPENAI_API_KEY not configured"}, status_code=503)
    from agent.evals.run import run_evals
    try:
        return run_evals(client, skills, policy)
    except Exception as exc:  # noqa: BLE001 - always return JSON the UI can read
        log_event("evals_error", error=str(exc))
        return JSONResponse({"error": f"eval run failed: {exc}"}, status_code=500)


@app.post("/api/reset")
def reset(user_id: str = "guest"):
    store.get(user_id, "admin", DEFAULT_MODEL, "subprocess").reset()
    return {"ok": True}


# --- chat (sync, simple) -----------------------------------------------------
@app.post("/api/chat")
def chat(req: ChatRequest):
    if client is None:
        return JSONResponse({"error": "OPENAI_API_KEY not configured"}, status_code=503)
    session = store.get(req.user_id, req.role, req.model, req.sandbox)
    with metrics.track(req.model):
        answer = session.agent.run(req.message)
    return {"answer": answer}


# --- chat (streaming over WebSocket) ----------------------------------------
@app.websocket("/ws")
async def ws_chat(ws: WebSocket):
    await ws.accept()
    if client is None:
        await ws.send_json({"type": "error", "message": "OPENAI_API_KEY not configured"})
        await ws.close()
        return
    loop = asyncio.get_event_loop()
    try:
        while True:
            req = await ws.receive_json()
            session = store.get(
                req.get("user_id", "guest"), req.get("role", "admin"),
                req.get("model", DEFAULT_MODEL), req.get("sandbox", "subprocess"),
            )
            queue: asyncio.Queue = asyncio.Queue()

            # The loop is synchronous; push its events onto the async queue from
            # the worker thread, thread-safely.
            def on_event(kind: str, data: dict):
                loop.call_soon_threadsafe(queue.put_nowait, {"type": kind, **data})

            def work() -> str:
                with metrics.track(req.get("model", DEFAULT_MODEL)):
                    return session.agent.run(req["message"], on_event=on_event)

            task = loop.run_in_executor(None, work)
            # Drain events until the worker finishes, then send the final answer.
            while not task.done() or not queue.empty():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.1)
                    await ws.send_json(event)
                except asyncio.TimeoutError:
                    pass
            answer = await task
            log_event("chat_done", user_id=req.get("user_id", "guest"), role=req.get("role"))
            await ws.send_json({"type": "done", "answer": answer})
    except WebSocketDisconnect:
        return


# --- static: deployed sites (P4) and the built React client ------------------
DEPLOYS = ROOT / "deploys"
DEPLOYS.mkdir(exist_ok=True)
app.mount("/sites", StaticFiles(directory=str(DEPLOYS), html=True), name="sites")

WEB_DIST = ROOT / "web" / "dist"
if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="web")
else:
    @app.get("/")
    def root_placeholder():
        return {"message": "API up. Build the client: cd web && npm install && npm run build."}
