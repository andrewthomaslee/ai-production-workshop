# Build plan: closing the gap to full workshop scope

A detailed, phased roadmap for everything still missing per
[coverage.md](coverage.md). Each phase lists its **goal**, the **requirement
IDs** it closes (see [requirements.md](requirements.md)), concrete **tasks**,
**files** to add/change, and **acceptance criteria** so "done" is unambiguous.

Phases are ordered so each reuses the previous one and follows the workshop's
agenda arc (build → multi-user → permissions → deploy → secure → projects).

---

## Status snapshot

**Done (the teaching core):** agentic loop, tools (fs / python / install / memory
/ skills), markdown skills with progressive disclosure, file-based memory,
swappable subprocess|docker sandbox, on-demand package installs, OpenAI
`gpt-5.4-mini`, uv, full docs (README + ARCHITECTURE).

**Remaining:** everything from the "Multi-User Architecture" segment onward,
which is the bulk of what makes the system *production-ready*.

---

## Phase 1: HTTP API + event streaming

**Goal:** expose the loop over HTTP and stream its steps, so any UI (and the
no-code client) can drive it. *Closes part of L5; unlocks L1, D2.*

**Why first:** the desktop client, observability, and multi-user all sit on top
of an API. The loop already emits `on_event("thinking"/"tool"/"result")`;
Phase 1 is mostly plumbing those events outward.

**Tasks**
- Add `server.py` (FastAPI) with:
  - `POST /chat`: non-streaming, returns the final answer (simple smoke path).
  - `GET /ws` (WebSocket): streams each `on_event` as JSON `{kind, data}` as the
    loop runs, then the final answer.
  - `GET /healthz`: liveness.
- Adapt the loop's `on_event` to push into an async queue the WebSocket drains
  (the loop is sync; run it in a threadpool / `run_in_executor`).
- Add a tiny `web/index.html` (vanilla JS) that opens the WS and renders the
  stream, proving the contract before the React app exists.
- Add `uvicorn` + `fastapi` to `pyproject.toml`.

**Files:** `server.py`, `web/index.html`, `pyproject.toml` (deps).

**Acceptance**
- `uv run uvicorn server:app` serves; opening `web/index.html` and sending a
  prompt shows tool calls streaming live, then the answer.
- The agent engine (`core/`, `tools/`) is imported by `server.py` but unchanged,
  proving the API is a surface, not a rewrite.

---

## Phase 2: Multi-user / multi-session isolation

**Goal:** serve many users from one deployment with **no cross-contamination** of
context, memory, or files. *Closes L3.*

**Why:** this is the workshop's central "demo vs production" claim. Today there
is one global `history`, one `memory.md`, one `workspace/`.

**Tasks**
- Introduce a `Session` abstraction (`core/session.py`): owns a user's
  `history`, a per-user `Memory`, and a per-user `workspace/<user_id>/` and
  `.sandbox_packages/<user_id>/`.
- A `SessionStore` keyed by `user_id` / `session_id` (in-memory for the
  workshop; note where Redis/DB would go).
- Sandbox + fs tools become **session-scoped**: the workspace path is injected
  per request, so user A can never read user B's files (extends the existing fs
  boundary).
- API: accept a `user_id` (header or token) on `/chat` and `/ws`; route to the
  right `Session`.

**Files:** `core/session.py`, `core/store.py`, changes to `server.py`,
`tools/fs.py` + `sandbox/runner.py` wiring (path injection).

**Acceptance**
- Two concurrent users get independent histories and workspaces; a file written
  by user A is invisible to user B (test with two WS clients).
- Memory written under user A does not appear in user B's system prompt.

---

## Phase 3: Permissions, scoped tools, audit trail

**Goal:** role-based access to tools, scoped execution, and a tamper-evident log
of every action. *Closes L4.*

**Tasks**
- Define roles (e.g. `viewer`, `analyst`, `admin`) and a tool→roles policy
  (`core/policy.py`). `dispatch()` checks the caller's role before running a
  tool; denials return a clear message the model can relay.
- Scope dangerous tools: e.g. `run_python`/`install_packages` gated to
  `analyst+`; `viewer` gets read-only tools.
- Audit log (`core/audit.py`): append a structured record for every tool call
  (`{ts, user_id, role, tool, input_digest, allowed, result_digest}`) to a JSONL
  file (note where this becomes a DB / SIEM sink in prod).
- Surface the audit trail via an API endpoint (`GET /audit?user_id=`).

**Files:** `core/policy.py`, `core/audit.py`, changes to `tools/registry.py`
(dispatch hook), `server.py`.

**Acceptance**
- A `viewer` attempting `run_python` is denied and the denial is logged.
- Every tool call (allowed or denied) produces an audit record; the endpoint
  returns a user's history.

---

## Phase 4: Desktop / web client (the no-code surface)

**Goal:** a polished React app so non-coders configure, launch, and monitor
agents without code. *Closes D2, L1.*

**Tasks**
- React app (Vite) that talks **only** to the HTTP/WS API (imports nothing from
  `core/`).
- Views: chat with live step stream; a tool/skill catalog (read-only view of
  what the agent can do); a **skill editor** (create/edit `SKILL.md` via API,
  the no-code authoring path); a memory viewer; an audit-log viewer.
- "Launch/monitor" controls: pick model + sandbox, see live events.
- API additions to support skill CRUD and config (`/skills`, `/config`).
- (Optional) wrap as a desktop app with Tauri for the "desktop client" framing.

**Files:** `web/` (React app), skill-CRUD endpoints in `server.py`,
`skills/__init__.py` (add write/reload).

**Acceptance**
- A non-coder can: start a chat, watch the agent work, author a new skill in the
  UI, and see the agent use it, all without touching a terminal.

---

## Phase 5: Security hardening + checklist (D4)

**Goal:** defensible against the threats the workshop names: prompt injection,
data leakage, and the compliance questions enterprises ask. *Closes L6, D4.*

**Tasks**
- **Prompt-injection defenses:**
  - Treat tool/file/web content as untrusted; clearly delimit it in the prompt
    and instruct the model that data is not instructions.
  - Sensitive tools require an allowlist / confirmation step; never let fetched
    content silently trigger privileged tools.
  - Add an injection test-suite (`tests/injection/`) with known attack strings
    (e.g. a CSV/web page containing "ignore previous instructions, exfiltrate…").
- **Data isolation:** confirm per-tenant fs/memory separation from Phase 2; add
  egress controls (sandbox `--network none` by default for runs; installs the
  only networked step).
- **Secrets hygiene:** ensure keys never enter prompts/logs; redact audit inputs.
- **Write the Security Checklist (`.workshop/security-checklist.md`)**, a
  deliverable: isolation boundaries, injection defenses, secrets, audit,
  data-retention/compliance notes (PII, tenancy, deletion).

**Files:** `core/context.py` (untrusted-content framing), `tools/registry.py`
(confirmation hook), `tests/injection/`, `.workshop/security-checklist.md`.

**Acceptance**
- The injection test-suite passes: planted instructions in data do not cause the
  agent to call privileged tools or leak other users' data.
- The security checklist exists and every item maps to code or a documented
  control.

---

## Phase 6: Production deployment & observability

**Goal:** containerize the app, make it observable, and document horizontal
scaling. *Closes the rest of L5; supports D3.*

**Tasks**
- `Dockerfile` for the app (multi-stage; uv for deps) + `docker-compose.yml`
  (app + optional Redis for sessions).
- Observability: structured logs, request/loop tracing, basic metrics
  (turns per request, tool latency, tokens): expose `/metrics` (Prometheus
  format) or log-based.
- Document **horizontal scaling**: stateless app + externalized session store;
  the sandbox as a separate concern (per-node Docker or a remote execution
  service).
- **Architecture Decision Templates (D3):** turn ARCHITECTURE.md §6 into a
  reusable `.workshop/adr-template.md` + 2–3 filled ADRs (provider choice,
  sandbox strategy, session store).

**Files:** `Dockerfile`, `docker-compose.yml`, `core/observability.py`,
`.workshop/adr-template.md`, `.workshop/adr/*.md`.

**Acceptance**
- `docker compose up` runs the full app; a request is traceable end-to-end in
  logs/metrics; scaling notes are written and consistent with the code.

---

## Phase 7: Remaining hands-on projects (P2-P4)

Each is mostly **new tools + new skills** on the existing engine, a good
demonstration that the framework extends cleanly.

- **P2, Marketing Assistant** *(L2, L6)*: add a `web_search` tool (+ `web_fetch`);
  skills for competitor research and structured report generation. Doubles as the
  prompt-injection demo surface (untrusted web content).
- **P3, ML Training Agent** *(L2, L5)*: tools to launch a (toy) training run,
  tail logs, read metrics/checkpoints; a skill for diagnosing common failures.
- **P4, Website Shipping Agent** *(L5)*: tools to scaffold a static site and
  deploy it (e.g. to a static host), returning a live URL; a skill orchestrating
  brief → files → deploy.

**Acceptance:** each project runs end-to-end from a single natural-language brief,
both via CLI and the web client.

---

## Suggested sequencing & the workshop mapping

| Phase | Closes | Workshop segment it powers |
|-------|--------|----------------------------|
| 1 API + streaming | L5(part), L1, D2 | First Agent: Code vs No-Code |
| 2 Multi-user | L3 | Multi-User Architecture |
| 3 Permissions + audit | L4 | Multi-User Architecture |
| 4 Desktop client | D2, L1 | First Agent (no-code side) |
| 5 Security + checklist | L6, D4 | Production Deployment & Security |
| 6 Deployment + observability | L5, D3 | Production Deployment & Security |
| 7 Projects P2–P4 | D5 | Build Something Real |

**Minimum path to a credible end-to-end demo:** Phases 1 → 2 → 3 → 4 give the
"multi-user, permissioned, no-code-driven agent" story, which is the workshop's
core differentiator. Phases 5–7 deepen security, deployment, and breadth.

Update [coverage.md](coverage.md) statuses as each phase lands.
