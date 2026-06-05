# Scaling & deployment notes

How this goes from one laptop to many users, and the one thing you must change
first.

## The current shape

```
            ┌─────────────────────────────────────────┐
  users ──▶ │  FastAPI app (server.py)                │
            │   ├─ SessionStore (IN MEMORY) ◀── state  │
            │   ├─ Policy + AuditLog                   │
            │   └─ agent engine (loop/tools/skills)    │
            │  sandbox: subprocess | docker            │
            └─────────────────────────────────────────┘
```

The app is *almost* stateless: every request carries its `user_id`, and all
per-user state lives in `Session` objects. The **only** thing preventing multiple
replicas is that the `SessionStore` is an in-process dict.

## The one change to scale out

Back the `SessionStore` with Redis (or any shared store):

1. Persist each `Session`'s history + memory pointer under a `user_id` key.
2. On request, load (or lazily create) the session from Redis instead of the dict.
3. Now any replica can serve any user → run N replicas behind a load balancer.

`Session` itself doesn't change; see [ADR-0003](../.workshop/adr/0003-in-memory-session-store.md).
Uncomment the `redis` service in `docker-compose.yml` to start.

## Containerization

```bash
docker compose up --build        # API + built React client on :8000
```

The [Dockerfile](../Dockerfile) is multi-stage: stage 1 builds the React client,
stage 2 runs the FastAPI app and serves that build. One image, one port.

## The sandbox at scale

Code execution is a separate scaling concern from the web tier:

- **Subprocess**: fine only for single-tenant / trusted use. Do not use with real
  users at scale.
- **Docker**: each `run_python` spins a throwaway container. At scale, run the
  sandbox as a **separate service / node pool** (or a managed execution service)
  so untrusted code never shares the web tier's host. The `Runner` interface makes
  this swap local; see [ADR-0002](../.workshop/adr/0002-swappable-sandbox.md).

## Observability

- Structured logs (JSON lines) via `agent/core/observability.py`.
- Metrics at `GET /api/metrics` (requests, errors, latency, by-model). Swap
  `Metrics.snapshot()` for a Prometheus exporter; the instrumentation points stay.
- Audit trail at `GET /api/audit`: ship the JSONL to an append-only store / SIEM.

## Production hardening checklist (excerpt)

Full list in [.workshop/security-checklist.md](../.workshop/security-checklist.md).
Before real users: externalize sessions (above), use the Docker (or stronger)
sandbox, drive roles from your IdP (don't trust a client role header), add rate
limits + per-tenant token budgets, and put secrets in a manager (not `.env`).
