"""ML Training tools for the ML Training Agent (P3): launch and monitor runs.

Self-contained: it does NOT train a real model (no GPU, no heavy deps).
Instead it *simulates* a training run deterministically: given hyperparameters it
produces a realistic loss/accuracy curve and writes per-epoch metrics to a job
directory in the workspace, just like a real trainer would. `training_status`
reads those metrics back.

The simulation has a real failure mode baked in: too high a learning rate makes
the loss diverge to NaN and the job is marked FAILED with a diagnosis. That gives
the agent something genuine to debug, which is the point of P3.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .base import Tool

_JOBS = "training"


def _job_dir(workspace: Path, job_id: str) -> Path:
    return workspace / _JOBS / job_id


class StartTraining(Tool):
    name = "start_training"
    description = (
        "Launch a (simulated) model training run with given hyperparameters and "
        "return a job_id plus a summary. Writes per-epoch metrics you can inspect "
        "with training_status. Note: a learning_rate that is too high will diverge "
        "(useful for practicing how to diagnose a bad run)."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "A short name for the run."},
            "epochs": {"type": "integer", "default": 10},
            "learning_rate": {"type": "number", "default": 0.1},
            "batch_size": {"type": "integer", "default": 32},
        },
        "required": ["name"],
    }

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)

    def run(self, name: str, epochs: int = 10, learning_rate: float = 0.1, batch_size: int = 32) -> str:
        job_id = f"{re_slug(name)}"
        d = _job_dir(self.workspace, job_id)
        d.mkdir(parents=True, exist_ok=True)

        metrics = []
        loss = 2.5  # starting cross-entropy-ish loss
        diverged = False
        for epoch in range(1, epochs + 1):
            # A stable step shrinks the loss; too large a step amplifies it.
            step = learning_rate * (loss - 0.2)
            loss = loss - step if learning_rate <= 1.0 else loss + abs(step) * learning_rate
            # Deterministic "noise" without RNG (keeps runs reproducible).
            loss += 0.02 * math.sin(epoch * 1.3)
            if loss != loss or loss > 1e4 or loss < 0:  # NaN/explosion guard
                diverged = True
                metrics.append({"epoch": epoch, "loss": "NaN", "accuracy": 0.0})
                break
            acc = max(0.0, min(0.99, 1.0 - loss / 2.5))
            metrics.append({"epoch": epoch, "loss": round(loss, 4), "accuracy": round(acc, 4)})

        status = {
            "job_id": job_id,
            "name": name,
            "hyperparameters": {"epochs": epochs, "learning_rate": learning_rate, "batch_size": batch_size},
            "state": "FAILED" if diverged else "COMPLETED",
            "epochs_run": len(metrics),
            "final_loss": metrics[-1]["loss"],
            "final_accuracy": metrics[-1]["accuracy"],
            "diagnosis": (
                f"Loss diverged to NaN by epoch {len(metrics)}. learning_rate={learning_rate} "
                f"is too high; try a value <= 0.5."
            ) if diverged else "Training converged normally.",
        }
        (d / "metrics.jsonl").write_text("\n".join(json.dumps(m) for m in metrics), encoding="utf-8")
        (d / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

        head = f"Started training '{name}' (job_id={job_id}). State: {status['state']}."
        return f"{head}\nFinal loss: {status['final_loss']}, accuracy: {status['final_accuracy']}.\n{status['diagnosis']}"


class TrainingStatus(Tool):
    name = "training_status"
    description = "Read the status and metrics of a training job by job_id (or list jobs if none given)."
    input_schema = {
        "type": "object",
        "properties": {"job_id": {"type": "string", "description": "Omit to list all jobs."}},
    }

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)

    def run(self, job_id: str | None = None) -> str:
        jobs_root = self.workspace / _JOBS
        if not job_id:
            if not jobs_root.exists():
                return "No training jobs yet."
            return "Jobs:\n" + "\n".join(f"- {p.name}" for p in sorted(jobs_root.iterdir()) if p.is_dir())
        d = _job_dir(self.workspace, job_id)
        status_file = d / "status.json"
        if not status_file.exists():
            return f"No job '{job_id}'. Use training_status with no job_id to list jobs."
        status = status_file.read_text(encoding="utf-8")
        metrics = (d / "metrics.jsonl").read_text(encoding="utf-8")
        return f"Status:\n{status}\n\nMetrics (per epoch):\n{metrics}"


def re_slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "run"
