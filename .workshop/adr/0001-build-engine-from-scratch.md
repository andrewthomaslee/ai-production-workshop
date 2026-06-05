# ADR-0001: Build the agent engine from scratch (no framework)

- **Status:** accepted
- **Date:** 2026-06-05
- **Deciders:** workshop authors

## Context
This is a teaching artifact whose primary goal is that learners *understand* how
an agent works. It also needs to be production-shaped (multi-user, permissions,
deployable). We must balance "readable enough to teach" against "real enough to
ship."

## Options considered
1. **LangChain / LlamaIndex / CrewAI / AutoGen**: batteries included, but they
   hide the agentic loop behind abstractions (chains, executors, graphs). Lots of
   surface area to explain; learners cargo-cult without understanding.
2. **From scratch on the raw provider SDK**: write the ~40-line loop ourselves,
   plus thin tool/skill/memory/sandbox modules. More code we own, but every part
   is visible and swappable.
3. **A thin wrapper over one framework**: compromise; still leaks framework
   concepts into the teaching.

## Decision
Build from scratch on the OpenAI SDK. The loop, tool registry, skills, memory,
and sandbox are all first-party modules small enough to read in one sitting.

## Consequences
- ✅ The "an agent is a while-loop" insight is directly visible in `core/loop.py`.
- ✅ Swapping providers (we moved Anthropic→OpenAI) touched two methods, proving
  the seams are clean.
- ⚠️ We re-implement things frameworks give free (retries, streaming helpers). We
  accept this for clarity; the pieces are small.
- Revisit if: the engine grows beyond what's teachable, or we need many provider
  integrations; then a thin adapter layer, still not a monolithic framework.
