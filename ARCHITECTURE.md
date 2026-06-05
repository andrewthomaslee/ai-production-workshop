# Architecture: a guided tour

This document is meant to be read **with the code open beside it**. By the end
you should be able to explain how an agent works to someone else, and modify
any part of this one with confidence.

The thesis of the whole project, in one sentence:

> An agent is a `while` loop that asks an LLM what to do, runs the tool the LLM
> asks for, feeds the result back, and repeats until the LLM is done.

Everything else (skills, memory, the sandbox) is just *what the LLM can see*
and *what it can do*. Hold onto that and the rest falls into place.

---

## 1. Read the code in this order

Each file is small and does one thing. Read them in this sequence; each builds
on the previous.

| # | File | What you'll learn |
|---|------|-------------------|
| 1 | [`agent/core/loop.py`](agent/core/loop.py) | The agentic loop. The whole idea lives here. |
| 2 | [`agent/core/context.py`](agent/core/context.py) | What the model *sees*: system prompt = base + skills + memory. |
| 3 | [`agent/tools/base.py`](agent/tools/base.py) | What a "tool" is: name + description + schema + `run()`. |
| 4 | [`agent/tools/registry.py`](agent/tools/registry.py) | How tools are advertised to the model and dispatched by name. |
| 5 | [`agent/tools/fs.py`](agent/tools/fs.py) | A concrete tool, and the **file-isolation** boundary. |
| 6 | [`agent/sandbox/runner.py`](agent/sandbox/runner.py) | The **code-execution-isolation** boundary (subprocess vs docker). |
| 7 | [`agent/tools/python.py`](agent/tools/python.py) | How a tool delegates to the sandbox without knowing how it works. |
| 8 | [`agent/skills/__init__.py`](agent/skills/__init__.py) + a `SKILL.md` | Skills as progressive disclosure. |
| 9 | [`agent/memory/store.py`](agent/memory/store.py) | Memory as a plain, human-readable file. |
| 10 | [`cli.py`](cli.py) | The **composition root**: where every part is built and wired. |

---

## 2. The mental model: four pillars around one loop

```
                        ┌─────────────────────────────┐
                        │        core/loop.py         │
       what it sees ───▶│   LLM call → tool → repeat  │◀─── what it can do
                        └─────────────────────────────┘
                          ▲                         ▲
            ┌─────────────┴───────────┐   ┌─────────┴──────────────┐
            │      core/context.py    │   │    tools/registry.py   │
            │  (assembles the prompt) │   │  (dispatch by name)    │
            └───┬─────────┬───────────┘   └──┬───────────┬─────────┘
                │         │                  │           │
          memory/store  skills/         tools/fs.py   tools/python.py
          (memory.md)   (SKILL.md)      (scoped I/O)        │
                                                            ▼
                                                    sandbox/runner.py
                                                  (subprocess | docker)
```

The **left side** is *perception* (what goes into the prompt). The **right
side** is *action* (what the model can invoke). The loop is the only thing that
touches both. Keep that split in mind; it's why the code is organized the way
it is.

---

## 3. The lifecycle of one request

Let's trace exactly what happens when you type:

```
you › Use run_python to compute 7 factorial, then tell me the number.
```

Follow along in [`agent/core/loop.py`](agent/core/loop.py); this is the single
most important thing to understand.

**Step 0: Startup (once).** [`cli.py`](cli.py) is the *composition root*. It
builds each subsystem independently (`Memory`, `SkillLibrary`, a sandbox
`Runner`, the `ToolRegistry`, the `Context`) then hands them to the `Agent`.
Notice nothing builds itself; the wiring is all in one readable place. This is
deliberate: to understand the system, you read one file and see every
connection.

**Step 1: Your message enters the transcript.**
```python
self.history.append({"role": "user", "content": user_message})
```
`history` is the running conversation. It grows over the whole session.

**Step 2: Build what the model sees, then ask it.**
```python
response = self.client.chat.completions.create(
    model=self.model,
    messages=[{"role": "system", "content": self.context.build()}] + self.history,
    tools=self.tools.schemas(),
)
```
Two assemblies happen here, every turn:
- `context.build()` ([context.py](agent/core/context.py)) stitches the system
  prompt from three parts: the base persona, the **skills catalog** (names +
  descriptions only, cheap), and **memory** (read back verbatim). Because it's
  rebuilt each turn, a fact the agent remembered five turns ago is present now.
- `tools.schemas()` ([registry.py](agent/tools/registry.py)) lists every tool
  in OpenAI's function-calling format. This is how the model knows `run_python`
  exists and what arguments it takes.

**Step 3: The model responds, and we record it.**
```python
message = response.choices[0].message
self.history.append(message)
```
The model can do one of two things: reply with text (it's done), or ask to call
a tool. We always append its turn to the transcript first; the API requires the
assistant's tool request to be in the history before the tool's result.

**Step 4: Did it ask for a tool?**
```python
if not message.tool_calls:
    return message.content or ""
```
For our prompt, the model *will* ask for a tool, so we skip this and continue.
(For a plain "hello", it wouldn't, and we'd return its text right here, a
one-iteration loop.)

**Step 5: Run each requested tool, feed results back.**
```python
for call in message.tool_calls:
    args = json.loads(call.function.arguments or "{}")
    output = self.tools.dispatch(call.function.name, args)
    self.history.append({"role": "tool", "tool_call_id": call.id, "content": output})
```
- OpenAI hands tool arguments as a **JSON string**, so we `json.loads` them.
- `dispatch` ([registry.py](agent/tools/registry.py)) looks the tool up by name
  and calls its `run()`. For `run_python`, that's
  [python.py](agent/tools/python.py), which immediately delegates to the
  sandbox `Runner` ([runner.py](agent/sandbox/runner.py)). The code executes,
  `print(math.factorial(7))` produces `5040`, and that string comes back.
- The result re-enters the transcript as a `role: "tool"` message, tied to the
  request by `tool_call_id`.

**Step 6: Loop.** Back to the top. `context.build()` and the now-longer
`history` (which includes the tool result `5040`) go to the model again. This
time it has what it needs, produces text (*"The factorial of 7 is 5040."*) with
no further tool calls, and Step 4 returns it.

That's the entire engine. Two API calls, one tool execution, and the loop
naturally stopped when the model had nothing left to ask for.

> **Why a loop and not a single call?** Because the model can't *do* anything
> itself; it can only emit text or request a tool. The loop is what closes the
> gap between "the model wants to run code" and "the code actually ran and here's
> the result." Multi-step tasks (read a file → analyze it → write a report) are
> just more iterations.

---

## 4. The four pillars in depth

### Tools: the only way to affect the world

A tool is four things, defined by the `Tool` base class
([base.py](agent/tools/base.py)):

```python
class Tool(ABC):
    name: str            # what the model calls
    description: str     # when/how to use it: the model reads this
    input_schema: dict   # JSON Schema for the arguments
    def run(self, **kwargs) -> str: ...   # do it, return text the model reads
```

The `description` and `input_schema` are not documentation for *you*; they are
the model's entire knowledge of the tool. A vague description means the model
misuses the tool. Treat them as prompt engineering.

The `ToolRegistry` ([registry.py](agent/tools/registry.py)) does two jobs:
`schemas()` advertises the tools to the API, and `dispatch()` runs one by name,
wrapping any exception into a readable string so the model can often recover
("Error: 'data.csv' does not exist" leads the model to list files and try again).

> **Provider isolation, in practice.** When we switched this project from
> Anthropic to OpenAI, the tools didn't change at all. They declare a neutral
> `input_schema`; only `registry.schemas()` (and the loop) know the
> provider-specific shape. That's the payoff of putting the format conversion in
> exactly one method.

### Skills: instructions loaded on demand (progressive disclosure)

A skill is a folder with a `SKILL.md` file ([example](agent/skills/data-analysis/SKILL.md)):

```markdown
---
name: data-analysis
description: Explore and analyze a dataset with pandas, then summarize findings.
---
<the full, detailed instructions>
```

The key idea is **progressive disclosure**:
- The system prompt only ever contains the skill's *name + description* (one
  line). Cheap: you can have fifty skills without bloating context.
- When the model judges a skill relevant, it calls `load_skill`
  ([skills.py](agent/tools/skills.py)), which returns the full body as a tool
  result. Only then does the detailed instruction enter context.

A skill contains **no code**. It's pure data, which is exactly why a non-coder
can author one by writing markdown. This is the seam where your no-code users
will live.

### Memory: a file the agent reads and writes

Memory ([store.py](agent/memory/store.py)) is deliberately the simplest thing
that works: a markdown file. The `remember` tool
([memory.py](agent/tools/memory.py)) appends one fact; `context.build()` reads
the whole file back into the system prompt every turn. No database, no
embeddings.

This is a teaching choice. "Memory" sounds mystical; seeing it is one `append`
and one `read` on a text file you can open in an editor demystifies it
completely. Watch `agent/memory/memory.md` change as you use `remember`.

### Sandbox: the one boundary between the model and your machine

This is the most important pillar for the "production-ready" theme, so it gets
its own section below.

---

## 5. The isolation boundaries (read this twice)

A demo becomes dangerous the moment the model can run code or touch files. This
project has **exactly two** boundaries, each in exactly one place:

**File isolation: [`tools/fs.py`](agent/tools/fs.py).** Every path the agent
gives is resolved against the workspace and rejected if it escapes:
```python
target = (self.workspace / path).resolve()
if not target.is_relative_to(self.workspace):
    raise ValueError(f"path '{path}' escapes the workspace")
```
The agent literally cannot read `../cli.py` or `/etc/passwd`. (Verify it: ask the
agent to read `../cli.py` and watch it get refused.)

**Code-execution isolation: [`sandbox/runner.py`](agent/sandbox/runner.py).**
Two interchangeable backends behind one `Runner` interface:

| Backend | Isolation | Setup | Use when |
|---------|-----------|-------|----------|
| `SubprocessRunner` | Runs as *you*, confined to the workspace dir + a timeout. Honestly weak. | None | Laptop, workshop, quick start |
| `DockerRunner` | Throwaway container, **no network**, memory/CPU caps, workspace mounted. | Docker | Anything resembling production |

The crucial property: **`run_python` and the loop are byte-for-byte identical
regardless of which backend is active.** Swapping `--sandbox subprocess` for
`--sandbox docker` changes which class `get_runner()` constructs and *nothing
else*. That is what "a clean isolation boundary" means in practice, and it's the
lesson to draw out: in a real deployment you'd harden this one file (gVisor,
Firecracker, a remote execution service) without touching the agent at all.

**On-demand packages.** The sandbox is intentionally separate from your project
environment, so `import pandas` fails at first. Rather than pre-installing
everything, the agent calls `install_packages`
([install.py](agent/tools/install.py)) when it hits a `ModuleNotFoundError`,
then retries. Packages land in a sandbox-only `.sandbox_packages/` directory
(added to `PYTHONPATH`), never your venv. Both backends implement `install()`
behind the same `Runner` interface: subprocess uses `uv pip install --target`,
docker installs into a mounted dir with network briefly enabled. Watch this in
the trace: a failed import, an install, a successful re-run. That self-recovery
loop is the agent pattern in miniature.

> **Honesty note for teaching.** The subprocess backend is intentionally weak and
> the code says so. Don't pretend it's safe; use it to motivate *why* the Docker
> backend exists. The gap between them is the entire "demo vs production" story in
> miniature.

---

## 6. Why these design choices (the "we chose X over Y" log)

- **From scratch, not LangChain/CrewAI.** Frameworks hide the loop, the one
  thing worth understanding. The whole engine here is ~70 lines you can read.
- **A flat `Tool` class, not decorators or auto-registration magic.** You can
  see every tool being constructed and registered in `cli.py`. No hidden
  discovery.
- **Markdown skills, not Python plugins.** Keeps skills authorable by non-coders
  and keeps "instructions" cleanly separate from "capabilities" (tools).
- **A markdown file for memory, not a vector DB.** The concept is the lesson;
  the storage is swappable. Upgrade it later without changing the `remember` tool.
- **Composition in one root (`cli.py`), not framework-managed DI.** The wiring
  *is* the architecture diagram. One file shows you everything.
- **`uv run python cli.py`, not an installed console script.** You run the file
  you read. No packaging indirection between you and the entry point.

---

## 7. Exercises (do these to really get it)

Ordered easy to hard. Each touches a different pillar.

1. **Add a tool.** Create a `get_time` tool (no sandbox needed) that returns the
   current time. Subclass `Tool`, register it in `cli.py`. *Goal: feel how little
   a capability costs.*
2. **Add a skill.** Write `skills/competitor-research/SKILL.md` describing how to
   research a competitor. Confirm it appears in the catalog and the agent loads
   it on a matching request. *Goal: see progressive disclosure work, no code.*
3. **Watch memory.** Tell the agent to remember three preferences across separate
   prompts, then `cat agent/memory/memory.md`. Restart the CLI and confirm it
   still knows them. *Goal: internalize "memory is just a file in the prompt."*
4. **Break, then defend, the file boundary.** Ask the agent to read `/etc/passwd`
   and watch `fs.py` refuse it. Then comment out the `is_relative_to` check and
   see what changes. Put it back. *Goal: understand that isolation is code you own.*
5. **Swap the sandbox.** Run a snippet that tries `import urllib.request;
   urllib.request.urlopen(...)` under `--sandbox subprocess` (it reaches the
   network) and under `--sandbox docker` (it can't, `--network none`). *Goal:
   see one boundary, two security postures, zero changes to the agent.*
6. **Add streaming.** The loop already emits `on_event("thinking"/"tool"/
   "result")`. Trace how `cli.py` renders those. This is the exact seam a web UI
   will hook into next. *Goal: see why the loop was built to be observed.*

---

## 8. The production layer (built on the same engine)

The teaching core above is wrapped, without modification, into a multi-user
service. Each piece is one module, in the same "isolation is visible" spirit:

| Concern | Module | What it adds |
|---------|--------|--------------|
| Multi-user | [`core/session.py`](agent/core/session.py) | A `Session` per user owns its own history, memory, workspace, and sandbox. `SessionStore` hands them out. No global state, so no data bleed. |
| Permissions | [`core/policy.py`](agent/core/policy.py) | Role to allowed tools. The registry *filters* tools before advertising them and *re-checks* at dispatch (defence in depth). |
| Audit | [`core/audit.py`](agent/core/audit.py) | Every tool call (allowed or denied) logged with who/role/tool/digest. |
| Observability | [`core/observability.py`](agent/core/observability.py) | Structured logs + metrics (`/api/metrics`). |
| API | [`server.py`](server.py) | FastAPI: `POST /api/chat`, a WebSocket that streams `on_event` steps, and skills/memory/audit/metrics endpoints. |
| No-code UI | [`web/`](web/) | A React client that talks ONLY to the API; it imports nothing from `agent/`. |

The key property held throughout: **the loop, tools, skills, memory, and sandbox
did not change.** Multi-user, permissions, and the API are layers *around* the
engine, not rewrites of it. The `on_event` callback the CLI used for colored
output is the exact same seam the WebSocket uses to stream to the browser.

This is the workshop's whole arc in one sentence: *the same small, readable
engine, made safe to hand to real users.* For the path beyond this repo
(Redis-backed sessions, IdP-driven roles, hardened sandboxes), see
[docs/SCALING.md](docs/SCALING.md) and [.workshop/security-checklist.md](.workshop/security-checklist.md).
