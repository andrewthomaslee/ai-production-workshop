# Production-Ready AI Agents: workshop framework

A from-scratch agent you can **read end-to-end**, that also runs as a
**multi-user, permissioned, deployable service** with a no-code web client. Built
to *show* the parts, not hide them, then show what it takes to put them in
production.

> **📖 Learning the engine?** Read **[ARCHITECTURE.md](ARCHITECTURE.md)**, a
> guided tour of the core (the loop, tools, skills, memory, sandbox) with a
> request trace and exercises.
>
> **🏭 Going to production?** This README covers the full system. Deep dives:
> [docs/SCALING.md](docs/SCALING.md) · [.workshop/security-checklist.md](.workshop/security-checklist.md) ·
> [.workshop/adr/](.workshop/adr/) (architecture decisions) ·
> [.workshop/plan.md](.workshop/plan.md) (build roadmap).

## What's in the box

```
            CLI (code-first)            React client (no-code)
                  │                            │
                  └----------  HTTP + WebSocket  ----------┘
                                   │
                              server.py  (FastAPI)
                                   │
        ┌---------------- one engine, many users ----------------┐
        │  SessionStore → Session per user (history · memory ·    │
        │                 workspace · sandbox, all ISOLATED)      │
        │  Policy (RBAC) · AuditLog · Metrics                     │
        │                                                         │
        │     core/loop.py   ← LLM call → tool → repeat           │
        │     tools/  skills/  memory/  sandbox/(subprocess|docker)│
        └─────────────────────────────────────────────────────────┘
```

The engine is the same whether you drive it from the CLI or the web client;
the UI is a *surface*, not a fork. It imports nothing from the engine.

## Quick start

Uses [uv](https://docs.astral.sh/uv/) (Python) and npm (client).

```bash
uv sync                                  # install Python deps from uv.lock
# Put your key in .env (git-ignored):  OPENAI_API_KEY=sk-...
```

**1. CLI (code-first, zero frontend):**
```bash
uv run python cli.py                      # subprocess sandbox
uv run python cli.py --sandbox docker     # real isolation
uv run python cli.py --model gpt-5.5      # frontier model (default: gpt-5.4-mini)
```

**2. API + no-code web client:**
```bash
cd web && npm install && npm run build && cd ..   # build the client once
uv run uvicorn server:app --port 8000             # serves API + client
# open http://127.0.0.1:8000
```
For client development with hot reload: `cd web && npm run dev` (proxies to the API).

**3. One-command container (production-ish):**
```bash
docker compose up --build                 # API + built client on :8000
```

> On a TLS-intercepting corporate network, set `WORKSHOP_INSECURE_SSL=1` so the
> web-research tool can reach the internet (dev only, never in real prod).

## The no-code client

`http://localhost:8000` is a "mission control" for agents:

- **Chat** with the agent and watch every step stream live (tool calls, results).
- **Role** selector (viewer / analyst / admin): flip it and watch tools lock in
  the **Capabilities** panel. RBAC made visible.
- **Skills** editor: author a skill in markdown; the agent can use it instantly.
  This is the no-code authoring path.
- **Memory**, **Audit**, and **Metrics** panels per user.

## The four projects (all built & working)

| Project | Try it (in chat) |
|---------|------------------|
| **Data Analysis** | "Create sales.csv with 5 rows, then chart revenue per product" |
| **Marketing Assistant** | "Research Anthropic and write a competitor brief to brief.md" |
| **ML Training** | "Train a model 'churn' with learning_rate 5.0; if it fails, fix it" |
| **Website Shipping** | "Build and deploy a landing page for a coffee brand 'Brewly'" |

## The pillars (each independently swappable)

| Pillar  | Where | One-line idea |
|---------|-------|---------------|
| Loop | `agent/core/loop.py` | LLM call → run tools → feed back → repeat |
| Tools | `agent/tools/*.py` | `name` + `schema` + `run()`. Add one = add one file |
| Skills | `agent/skills/*/SKILL.md` | Markdown instructions, loaded on demand. No code |
| Memory | `agent/memory/store.py` | A file the agent appends to and reads back |
| Sandbox | `agent/sandbox/runner.py` | The one boundary; `subprocess` or `docker` |
| **Sessions** | `agent/core/session.py` | Per-user isolation of all of the above |
| **Permissions** | `agent/core/policy.py` | Role → allowed tools, enforced + filtered |
| **Audit** | `agent/core/audit.py` | Every tool call logged: who/role/tool/allowed |

## Testing (two layers)

Production-ready means you can prove it still works after you change it. This app
has two complementary test layers, both runnable from the **Tests** tab in the
client or the command line.

```bash
# 1. Boundary tests: deterministic, no API key. The mechanical guarantees.
uv run python -m scripts.test_suite        # 19 checks, runs in ms

# 2. Agent evals: runs the REAL agent on scenarios, graded programmatically
#    AND by an LLM judge. Catches BEHAVIORAL regressions. Needs OPENAI_API_KEY.
uv run python -m agent.evals.run           # 7 scenarios, ~30s

# (also) live WebSocket streaming smoke test against a running server
uv run python scripts/ws_test.py 8000
```

- **Boundary tests** ([`scripts/test_suite.py`](scripts/test_suite.py)) cover the
  plumbing that must never leak: filesystem scoping, role-based tool filtering,
  audit logging, tenant isolation, and the project tools (including a deploy that
  serves a real live URL). No model, so they're instant and never flaky.
- **Agent evals** ([`agent/evals/`](agent/evals/)) run the actual agent and grade
  what it *did*: `tool_called`, `memory_excludes("PWNED")`, `url_serves(...)`
  (programmatic), plus an **LLM-as-judge** for quality. Scenarios span capability,
  memory, security (injection refusal), permissions (RBAC), and answer quality.
  Add a case in [`agent/evals/cases.py`](agent/evals/cases.py) whenever you fix a
  bug, so it can never silently come back.

Both are exposed over the API (`POST /api/tests`, `POST /api/evals`) and rendered
as a live pass/fail board in the client, judge reasoning and all.

## Add your own

- **A tool:** subclass `Tool` (see `agent/tools/fs.py`), add it in
  `agent/core/session.py` → `build_tools`, and grant it to roles in
  `agent/core/policy.py`.
- **A skill:** create `agent/skills/<name>/SKILL.md` with `name`/`description`
  front matter, or write one in the client's Skills editor. No restart.

## Project layout

```
agent/        the engine (core, tools, skills, memory, sandbox)
agent/evals/  behavioral evals: real agent + programmatic checks + LLM judge
server.py     FastAPI: HTTP + WebSocket, multi-user, RBAC, audit, metrics, tests
cli.py        single-user REPL over the same engine
web/          React + Vite no-code client (Tests tab runs both test layers)
scripts/      test_suite.py (deterministic boundary tests), ws_test.py
slides/       the workshop deck (workshop.pptx) + generator
docs/         SCALING.md
.workshop/    requirements, coverage, plan, security checklist, ADRs
Dockerfile, docker-compose.yml   one-image deployment
```
