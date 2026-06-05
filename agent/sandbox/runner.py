"""Code-execution isolation: the single boundary between the model and the host.

Two interchangeable backends behind one `Runner` interface:

  - SubprocessRunner : zero setup, runs anywhere. Weaker isolation; the code
                       runs as your user, only constrained to the workspace dir
                       and a timeout. Honest default for a laptop/workshop.
  - DockerRunner     : real isolation. Runs in a throwaway container with no
                       network and the workspace mounted. The "production" upgrade.

Both can `install()` packages on demand into a sandbox-local directory that is
SEPARATE from your project's environment, so the agent can `import pandas`
without you pre-installing anything and without polluting the project venv.
That install dir is added to PYTHONPATH for every run.

Swapping `--sandbox subprocess|docker` changes ONLY which class is built.
Everything upstream (the run_python tool, the loop) is unaffected. That is the
whole didactic point of putting isolation behind one interface.
"""

from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path


class Runner(ABC):
    @abstractmethod
    def run(self, code: str) -> str:
        ...

    @abstractmethod
    def install(self, packages: list[str]) -> str:
        ...


class SubprocessRunner(Runner):
    def __init__(self, workspace: Path, timeout: int = 30):
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        # Packages live OUTSIDE the workspace and outside the project venv, in a
        # sandbox-only directory. Installed once, importable by every run.
        self.packages_dir = (self.workspace.parent / ".sandbox_packages" / "local").resolve()
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    def _env(self) -> dict:
        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(self.packages_dir) + (os.pathsep + existing if existing else "")
        return env

    def run(self, code: str) -> str:
        try:
            proc = subprocess.run(
                ["python3", "-c", code],
                cwd=self.workspace,          # confined to the workspace
                env=self._env(),             # sandbox packages on the path
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return f"Error: execution exceeded {self.timeout}s timeout"
        return _format(proc.stdout, proc.stderr, proc.returncode)

    def install(self, packages: list[str]) -> str:
        # The sandbox python is a uv venv with no pip, so install with uv into
        # our target dir. (uv is the project's package manager.)
        try:
            proc = subprocess.run(
                ["uv", "pip", "install", "--target", str(self.packages_dir), *packages],
                capture_output=True,
                text=True,
                timeout=180,
            )
        except FileNotFoundError:
            return "Error: 'uv' not found; cannot install packages."
        except subprocess.TimeoutExpired:
            return "Error: package install timed out"
        if proc.returncode != 0:
            return f"Install failed:\n{proc.stderr.strip()}"
        return f"Installed: {', '.join(packages)}"


class DockerRunner(Runner):
    def __init__(self, workspace: Path, image: str = "python:3.11-slim", timeout: int = 30):
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        # Separate dir from the subprocess backend; its packages are built for a
        # different Python (3.11 in the image) and must not be mixed.
        self.packages_dir = (self.workspace.parent / ".sandbox_packages" / "docker").resolve()
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        self.image = image
        self.timeout = timeout

    def run(self, code: str) -> str:
        return self._docker(
            ["python3", "-c", code],
            timeout=self.timeout,
            network="none",  # no egress while running model-written code
        )

    def install(self, packages: list[str]) -> str:
        # Installing needs the network; running does not. The mounted packages
        # dir persists installs across the throwaway containers.
        out = self._docker(
            ["pip", "install", "--target", "/pkgs", *packages],
            timeout=180,
            network="bridge",
        )
        return out if out.startswith("Error") else f"Installed: {', '.join(packages)}\n{out}"

    def _docker(self, cmd: list[str], timeout: int, network: str) -> str:
        try:
            proc = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "--network", network,
                    "--memory", "512m", "--cpus", "1",
                    "-e", "PYTHONPATH=/pkgs",
                    "-v", f"{self.workspace}:/work",
                    "-v", f"{self.packages_dir}:/pkgs",
                    "-w", "/work",
                    self.image, *cmd,
                ],
                capture_output=True,
                text=True,
                timeout=timeout + 15,  # allow for container startup
            )
        except subprocess.TimeoutExpired:
            return f"Error: execution exceeded {timeout}s timeout"
        except FileNotFoundError:
            return "Error: docker not found. Use --sandbox subprocess instead."
        return _format(proc.stdout, proc.stderr, proc.returncode)


def get_runner(kind: str, workspace: Path) -> Runner:
    if kind == "docker":
        return DockerRunner(workspace)
    if kind == "subprocess":
        return SubprocessRunner(workspace)
    raise ValueError(f"unknown sandbox '{kind}' (use 'subprocess' or 'docker')")


def _format(stdout: str, stderr: str, code: int) -> str:
    out = stdout.strip()
    err = stderr.strip()
    parts = []
    if out:
        parts.append(out)
    if err:
        parts.append(f"[stderr]\n{err}")
    if code != 0:
        parts.append(f"[exit code {code}]")
    return "\n".join(parts) if parts else "(no output)"
