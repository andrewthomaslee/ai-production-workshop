"""Run Python code.

This tool is deliberately thin: it just hands the code to a sandbox runner.
ALL of the isolation logic lives in agent/sandbox/; this file doesn't know
or care whether the code runs in a subprocess or a Docker container. That's
the point: the execution-isolation boundary is in exactly one place.
"""

from __future__ import annotations

from .base import Tool
from ..sandbox.runner import Runner


class RunPython(Tool):
    name = "run_python"
    description = (
        "Execute a Python 3 snippet in a sandbox and return its stdout/stderr. "
        "The snippet runs in the workspace directory, so it can read/write files "
        "you created there. Use print() to see results."
    )
    input_schema = {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "Python source to execute."}},
        "required": ["code"],
    }

    def __init__(self, runner: Runner):
        self.runner = runner

    def run(self, code: str) -> str:
        return self.runner.run(code)
