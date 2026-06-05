"""Long-term memory: a plain markdown file.

Deliberately the simplest thing that works. Memory is human-readable and
human-editable. There is no database and no embedding store; for teaching,
"memory is a file the agent appends to and reads back" is the whole idea.
"""

from __future__ import annotations

from pathlib import Path


class Memory:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def read(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def append(self, fact: str) -> None:
        line = f"- {fact.strip()}\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line)
