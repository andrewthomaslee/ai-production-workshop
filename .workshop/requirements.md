# Workshop requirements: analysis

> Source: the event listing for **"Building Production-Ready AI Applications:
> Hands-On Workshop"** by Gabriele Venturi (Packt). This document distills that
> prose into concrete, trackable requirements so the scaffold can be built and
> checked against them.

## 1. Core thesis

The workshop's premise: **getting an AI demo working is easy; making it
production-ready is the hard part.** Production-ready means it can:

- handle real, concurrent users
- enforce permissions
- not leak data

Every concept is taught **twice (once with code, once no-code)**, and the
attendee picks the path that fits them.

## 2. Audiences (must serve all three)

| Audience | Need |
|----------|------|
| No-code (PMs, founders, operators) | Deploy & manage agents through a **visual desktop client**, no code |
| Code-first (SW/backend/ML engineers) | Build from scratch with **full control** over architecture & tooling |
| Both | Understand what it takes to go **prototype to reliable system** |

**Implication for the scaffold:** one engine, two surfaces. The code-first path
and the no-code client must be the *same* system, not two codebases; otherwise
the "built twice" promise is dishonest.

## 3. Learning objectives (the syllabus)

Extracted as discrete capabilities the material must demonstrate:

- **L1: No-code deploy/manage:** configure, launch, monitor agents from a
  desktop client.
- **L2: Modular architecture (code):** skills, tools, memory, and orchestration
  patterns that scale.
- **L3: Multi-user systems:** isolate context, manage per-user state, serve many
  users safely from one deployment.
- **L4: Permissions & scoped execution:** role-based permissions, scoped tool
  execution, **audit trails** for enterprise.
- **L5: Production deployment:** containerization, API design, observability,
  horizontal scaling.
- **L6: Security:** prompt-injection defense, data isolation, compliance
  considerations for enterprise deals.

## 4. Deliverables promised to attendees

These are things the attendee leaves with; the scaffold/repo should make each
real:

- **D1**: A production-ready **agent framework** they can extend.
- **D2**: A **desktop client** for managing/interacting with agents (no code
  needed).
- **D3**: **Architecture decision templates** for AI system design.
- **D4**: A **security checklist** for production AI deployments.
- **D5**: All workshop **code and project files**.
- (Plus: event recording, certificates.)

## 5. Hands-on projects (each built code + no-code)

| ID | Project | What it does | Exercises which objectives |
|----|---------|--------------|----------------------------|
| P1 | **Data Analysis Agent** | Conversational analytics: executes code, interprets results, answers questions about any dataset | L2 (tools/skills/sandbox), L5 |
| P2 | **Marketing Assistant** | Multi-tool agent: drafts campaigns, researches competitors, generates structured reports | L2 (multi-tool orchestration), L6 (web/injection) |
| P3 | **ML Training Agent** | Configure, monitor, and debug ML training runs | L2, L5 (observability) |
| P4 | **Website Shipping Agent** | Brief to deployed site in seconds, prompt to live URL | L5 (deployment, end-to-end) |

## 6. Agenda to requirement mapping

| Segment (time) | Must demonstrate |
|----------------|------------------|
| Welcome + Context (20m) | The demo-vs-production gap; a <5-min "deploy a working agent" wow moment |
| First Agent: Code vs No-Code (45m) | Build P1 **both ways**, side by side (L1, L2) |
| Multi-User Architecture & Permissions (40m) | Context isolation, per-user state, RBAC, audit trails, **live** (L3, L4) |
| Production Deployment & Security (45m) | Containerization, API design, observability, scaling; prompt-injection defense, data isolation, compliance (L5, L6) |
| Build Something Real (50m) | Attendee builds one of P1-P4, their chosen path, takes it home |
| Live Q&A (30m) | Architecture deep dives, war stories |

## 7. Derived non-functional requirements

From the above, the framework itself must be:

- **Readable / didactic**: concepts visible, not hidden behind abstractions
  (it's a teaching artifact first).
- **Modular**: skills, tools, memory, orchestration each swappable in isolation.
- **Multi-tenant-ready**: per-user context & state isolation is a first-class
  concern, not bolted on.
- **Observable**: emits events that a UI and a logging/audit layer can consume.
- **Secure by construction**: clear, single-location isolation boundaries
  (filesystem, code execution, data); defensible against prompt injection.
- **Deployable**: containerizable, with a clean API surface for horizontal
  scaling.

See [coverage.md](coverage.md) for how the current scaffold maps to all of the
above, and what's still missing.
