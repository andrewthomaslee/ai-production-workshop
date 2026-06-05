# ADR-0003: In-memory SessionStore now, Redis-ready boundary

- **Status:** accepted
- **Date:** 2026-06-05
- **Deciders:** workshop authors

## Context
Multi-user is the workshop's central "demo vs production" lesson. We need
per-user isolation (history, memory, workspace, permissions) and a story for
horizontal scaling, without drowning the teaching in infrastructure.

## Options considered
1. **Global state**: what most demos do. Rejected: it's exactly the anti-pattern
   we're teaching against (one user can see another's data).
2. **In-memory `SessionStore` keyed by user_id**: clean per-user `Session`
   objects, no external dependency, trivial to run.
3. **Redis/DB-backed sessions from day one**: production-correct but adds setup
   and obscures the core idea for learners.

## Decision
Ship an in-memory `SessionStore` (`agent/core/session.py`) that hands out one
isolated `Session` per user. Mark (in code comments and docs) exactly where a
Redis/DB implementation slots in (the store is the only stateful seam).

## Consequences
- ✅ Per-user isolation is real and testable today (verified: user A's files and
  memory are invisible to user B).
- ✅ The scaling path is a single, well-marked swap, covered in `docs/SCALING.md`.
- ⚠️ A single in-memory store means one process / one worker for correctness.
  Horizontal scaling requires the Redis swap first; documented, not hidden.
- Revisit when: you need more than one worker/replica, or sessions must survive a
  restart. Then implement `SessionStore` over Redis; `Session` itself is unchanged.
