"""Audit trail: an append-only record of every tool call.

For enterprise use you must be able to answer "who did what, when, and was it
allowed?" This writes one JSON line per tool invocation (allowed or denied) to a
JSONL file. We store *digests/previews* of inputs and outputs, not the full
payloads, so the log doesn't become a place sensitive data leaks to.

In production this sink becomes a database or a SIEM; the record shape is the
part that matters and it stays the same.
"""

from __future__ import annotations

import json
from pathlib import Path


def _preview(value, limit: int = 200) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "…"


class AuditLog:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq = 0
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def record(self, *, user_id: str, role: str, tool: str,
               tool_input: dict, allowed: bool, result: str) -> None:
        self._seq += 1
        entry = {
            "seq": self._seq,
            "user_id": user_id,
            "role": role,
            "tool": tool,
            "allowed": allowed,
            "input_preview": _preview(tool_input),
            "result_preview": _preview(result),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def entries(self, user_id: str | None = None) -> list[dict]:
        if not self.path.exists():
            return []
        rows = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if user_id is not None:
            rows = [r for r in rows if r.get("user_id") == user_id]
        return rows
