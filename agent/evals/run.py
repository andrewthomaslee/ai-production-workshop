"""Run the eval suite, from the CLI or the server.

`run_evals(...)` builds an isolated, throwaway environment (each case gets its
own fresh Session under a temp dir, so re-runs never see stale state) and grades
every case. Both the CLI (`python -m agent.evals.run`) and the API endpoint call
the same function, so what you see in the terminal is what the UI shows.
"""

from __future__ import annotations

import itertools
import os
import tempfile
from pathlib import Path

from .cases import CASES
from .harness import EvalCase, run_suite

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "gpt-5.4-mini"


def _make_session_factory(root: Path, skills, client, policy, model: str):
    """Returns make_session(case) -> a fresh, isolated Session for that case."""
    from ..core.session import Session

    counter = itertools.count()

    def make(case: EvalCase) -> Session:
        # Unique user_id per case AND per run, so nothing leaks between runs.
        uid = f"eval-{case.name}-{next(counter)}"
        return Session(
            uid, case.role, model, "subprocess",
            root=root, skills=skills, client=client, policy=policy, audit=None,
        )

    return make


def run_evals(client, skills, policy, *, model: str = DEFAULT_MODEL,
              judge_model: str = DEFAULT_MODEL, cases=None, max_workers: int = 4) -> dict:
    """Run the suite with provided app singletons. Returns the structured summary."""
    cases = cases if cases is not None else CASES
    root = Path(tempfile.mkdtemp(prefix="agent-evals-"))
    make = _make_session_factory(root, skills, client, policy, model)
    ctx = {"client": client, "judge_model": judge_model}
    return run_suite(cases, make, ctx, max_workers=max_workers)


def list_cases() -> list[dict]:
    """Metadata for the UI, without running anything."""
    return [{
        "name": c.name,
        "category": c.category,
        "description": c.description,
        "role": c.role,
        "checks": [{"label": ch.label, "kind": ch.kind} for ch in c.checks],
    } for c in CASES]


def main() -> None:
    from dotenv import load_dotenv
    from openai import OpenAI

    from ..core.policy import Policy
    from ..skills import SkillLibrary

    load_dotenv()
    if not os.environ.get("OPENAI_API_KEY", "").startswith("sk-"):
        raise SystemExit("Set OPENAI_API_KEY in .env to run agent evals.")

    client = OpenAI()
    skills = SkillLibrary(ROOT / "agent" / "skills")
    policy = Policy()

    print("\n=== Agent evals (runs the real agent; programmatic + LLM-judge) ===\n")
    summary = run_evals(client, skills, policy)

    G, R, B, RST = "\033[32m", "\033[31m", "\033[2m", "\033[0m"
    for r in summary["results"]:
        mark = f"{G}PASS{RST}" if r["passed"] else f"{R}FAIL{RST}"
        print(f"[{mark}] {r['name']:18} {B}{r['category']:11} {r['duration']:>5}s{RST}")
        for c in r["checks"]:
            cm = f"{G}✓{RST}" if c["passed"] else f"{R}✗{RST}"
            tag = "judge" if c["kind"] == "judge" else "prog "
            print(f"        {cm} [{tag}] {c['label']}  {B}{c['detail']}{RST}")
        print()

    cat = "  ".join(f"{k} {v['passed']}/{v['total']}" for k, v in summary["by_category"].items())
    print(f"=== {summary['passed']}/{summary['total']} cases passed ===")
    print(f"    {cat}\n")
    if summary["passed"] != summary["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
