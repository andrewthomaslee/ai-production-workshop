"""The `install_packages` tool.

Like `run_python`, this is a thin delegate to the sandbox `Runner`; it doesn't
know whether packages land in a local directory or a container. It lets the
agent recover from a `ModuleNotFoundError` by installing what it needs, then
retrying its code. The packages go into a sandbox-only directory, never your
project environment.
"""

from __future__ import annotations

from .base import Tool
from ..sandbox.runner import Runner


class InstallPackages(Tool):
    name = "install_packages"
    description = (
        "Install Python packages into the sandbox so run_python can import them. "
        "Use this when a snippet fails with ModuleNotFoundError, then re-run the code. "
        "Pass package names as you would to pip, e.g. ['pandas', 'matplotlib']."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "packages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Package names to install.",
            }
        },
        "required": ["packages"],
    }

    def __init__(self, runner: Runner):
        self.runner = runner

    def run(self, packages: list[str]) -> str:
        return self.runner.install(packages)
