"""Observability: structured logs + lightweight metrics.

Production systems must be inspectable: you need to answer "how many requests,
how slow, how many errors, which model" without attaching a debugger. This gives:

  - log_event(): one structured JSON line per notable event (greppable, ship to
    any log aggregator).
  - Metrics: in-process counters/timers exposed at GET /api/metrics.

Deliberately dependency-free (no Prometheus client) so it's readable. In a real
deployment you'd swap `snapshot()` for a Prometheus exporter or OpenTelemetry;
the instrumentation points (where track() and log_event() are called) stay put.
"""

from __future__ import annotations

import json
import sys
import time
from contextlib import contextmanager


def log_event(event: str, **fields) -> None:
    """Emit one structured log line to stdout."""
    record = {"event": event, **fields}
    print(json.dumps(record, default=str), file=sys.stdout, flush=True)


class Metrics:
    def __init__(self):
        self.requests = 0
        self.errors = 0
        self.total_seconds = 0.0
        self.by_model: dict[str, int] = {}

    @contextmanager
    def track(self, model: str):
        self.requests += 1
        self.by_model[model] = self.by_model.get(model, 0) + 1
        start = time.perf_counter()
        try:
            yield
        except Exception:
            self.errors += 1
            raise
        finally:
            self.total_seconds += time.perf_counter() - start

    def snapshot(self) -> dict:
        avg = self.total_seconds / self.requests if self.requests else 0.0
        return {
            "requests": self.requests,
            "errors": self.errors,
            "avg_seconds": round(avg, 3),
            "by_model": self.by_model,
        }
