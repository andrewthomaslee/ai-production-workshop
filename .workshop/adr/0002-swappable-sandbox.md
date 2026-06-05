# ADR-0002: Code execution behind one swappable sandbox interface

- **Status:** accepted
- **Date:** 2026-06-05
- **Deciders:** workshop authors

## Context
The agent runs model-written Python. That is the single most dangerous thing it
does. We need an isolation story that is (a) zero-setup for a laptop/workshop and
(b) honest about the security tradeoff, with a clear upgrade path to real
isolation.

## Options considered
1. **Subprocess only**: trivial, runs anywhere, but weak isolation (runs as the
   user). Fine for a demo, dangerous for real users.
2. **Docker only**: strong isolation (no network, resource caps, throwaway
   container) but requires Docker installed, a setup hurdle in a live workshop.
3. **Both, behind one `Runner` interface**: pick per run with `--sandbox`.

## Decision
Define a `Runner` interface with two implementations (`SubprocessRunner`,
`DockerRunner`) in `agent/sandbox/runner.py`. Default to subprocess for zero
setup; Docker is one flag away. The `run_python` tool and the loop are identical
regardless of backend.

## Consequences
- ✅ One file is the entire code-execution boundary: easy to teach, easy to audit.
- ✅ Upgrade path is real: in prod you replace this one file (gVisor, Firecracker,
  a remote execution service) without touching the agent.
- ✅ The subprocess backend's weakness is documented, not hidden; it motivates
  *why* Docker exists.
- ⚠️ Two backends to keep in sync (e.g. on-demand package installs implemented
  twice). Accepted; the interface keeps them honest.
- Revisit if: we need per-tenant network policy or GPU sandboxes; add a third
  `Runner`, interface unchanged.
