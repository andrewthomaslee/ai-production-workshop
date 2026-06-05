"""Agent evals: behavioral regression tests for the agent itself.

Two layers of testing protect this app:
  - scripts/test_suite.py : deterministic boundary tests (no LLM) - the plumbing
  - agent/evals/          : behavioral evals (real agent + LLM-judge) - the behavior

See run.py for the entry point and cases.py for the scenarios.
"""

# Lazy re-exports so `python -m agent.evals.run` doesn't import run.py twice.
__all__ = ["run_evals", "list_cases"]


def __getattr__(name):
    if name in __all__:
        from . import run as _run
        return getattr(_run, name)
    raise AttributeError(name)
