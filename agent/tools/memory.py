"""The `remember` tool.

The only way the agent writes to long-term memory. It appends a single fact
to memory/memory.md, which Context reads back into the system prompt every
turn. Students can open that file and literally watch the agent learn.
"""

from __future__ import annotations

from .base import Tool
from ..memory.store import Memory


class Remember(Tool):
    name = "remember"
    description = (
        "Save a short fact to long-term memory so you recall it in future turns "
        "and future sessions. Use for stable preferences, names, decisions, not "
        "for transient working notes."
    )
    input_schema = {
        "type": "object",
        "properties": {"fact": {"type": "string", "description": "One concise fact to remember."}},
        "required": ["fact"],
    }

    def __init__(self, memory: Memory):
        self.memory = memory

    def run(self, fact: str) -> str:
        self.memory.append(fact)
        return f"Remembered: {fact}"
