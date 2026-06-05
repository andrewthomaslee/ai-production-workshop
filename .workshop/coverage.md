# Coverage: scaffold vs. requirements

How the scaffold maps to [requirements.md](requirements.md). **Status: full build
complete**; all phases of [plan.md](plan.md) implemented and tested.

Legend: ✅ done · 🟡 partial · ⬜ not started

## Learning objectives

| ID | Objective | Status | Where |
|----|-----------|--------|-------|
| L1 | No-code deploy/manage via client | ✅ | `web/` React client: chat, RBAC, skill editor, memory/audit/metrics |
| L2 | Modular architecture | ✅ | `agent/core/loop.py`, `tools/`, `skills/`, `memory/`, `sandbox/` |
| L3 | Multi-user isolation | ✅ | `agent/core/session.py`: per-user history/memory/workspace/sandbox |
| L4 | Permissions + scoped tools + audit | ✅ | `policy.py`, `audit.py`, enforced in `tools/registry.py` |
| L5 | Production deployment | ✅ | `Dockerfile`, `docker-compose.yml`, `observability.py`, `docs/SCALING.md` |
| L6 | Security | ✅ | injection framing in `context.py`, isolation boundaries, `security-checklist.md` |

## Deliverables

| ID | Deliverable | Status | Where |
|----|-------------|--------|-------|
| D1 | Extensible agent framework | ✅ | `agent/` + add-a-tool/skill docs |
| D2 | No-code desktop client | ✅ | `web/` (React + Vite), served by FastAPI |
| D3 | Architecture decision templates | ✅ | `.workshop/adr-template.md` + 3 filled ADRs |
| D4 | Security checklist | ✅ | `.workshop/security-checklist.md` (10 controls) |
| D5 | All code & project files | ✅ | engine, server, client, 4 projects, test suite, slides |

## Hands-on projects

| ID | Project | Status | Tools / skill |
|----|---------|--------|---------------|
| P1 | Data Analysis | ✅ | run_python + install_packages + `data-analysis` skill |
| P2 | Marketing Assistant | ✅ | `web_search`/`web_fetch` + `marketing-assistant` skill |
| P3 | ML Training | ✅ | `start_training`/`training_status` + `ml-training` skill |
| P4 | Website Shipping | ✅ | `deploy_site` (live URL) + `website-shipping` skill |

## Non-functional

| Requirement | Status | Notes |
|-------------|--------|-------|
| Readable / didactic | ✅ | Small files, reading order, request trace, exercises |
| Modular / swappable | ✅ | Provider + sandbox swaps proved the seams |
| Observable | ✅ | `on_event` stream, `/api/metrics`, structured logs, audit |
| Secure by construction | ✅ | fs + code-exec boundaries; injection-resistant; checklist |
| Multi-tenant-ready | ✅ | Per-session isolation, verified by tests |
| Deployable | ✅ | Docker image builds AND runs (API + SPA), compose up |

## Testing (two layers, both in the UI)

| Layer | Where | What it proves |
|-------|-------|----------------|
| Boundary tests (deterministic, no LLM) | `scripts/test_suite.py` · `POST /api/tests` | The plumbing can't leak: fs scoping, RBAC, audit, isolation, tools |
| Agent evals (real agent + LLM judge) | `agent/evals/` · `POST /api/evals` | The behavior is right: capability, memory, injection refusal, RBAC, quality |

Both render as a live pass/fail board in the client's **Tests** tab. Run them on
every change to catch regressions before users do.

## Verification performed

- **Deterministic suite**: 19/19 (`uv run python -m scripts.test_suite`): fs
  scoping, RBAC filtering, audit, tenant isolation, training, live-URL deploy.
- **Agent evals**: 7/7 (`uv run python -m agent.evals.run`): programmatic + LLM
  judge across capability/memory/security/permissions/quality; verified via the
  API and the client's Tests tab (judge reasoning shown per case).
- **Live API** (curl + WebSocket): chat, streaming, multi-user isolation (Alice's
  file invisible to Bob), RBAC (viewer denied run_python), audit logging.
- **All four projects** end-to-end via the API.
- **Security**: prompt-injection attempt refused (memory stayed clean);
  analyst's deploy denied (admin-only).
- **Web client**: verified in a real browser: render, live RBAC, full streaming
  chat (8-step ML-training run), all side panels.
- **Docker**: image builds; container runs and serves API + SPA with key detected.

## What's intentionally left for "real prod" (documented, not hidden)

These are called out in the security checklist / ADRs as the next steps beyond
workshop scope: externalize the session store to Redis for multi-replica
scaling, drive roles from an IdP (not a client header), per-tenant rate limits +
token budgets, secrets manager, and a hardened sandbox (gVisor/Firecracker) for
untrusted code at scale.
