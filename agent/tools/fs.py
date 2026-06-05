"""Filesystem tools, scoped to a single workspace directory.

The scoping is the lesson: the agent can only touch files under `workspace`.
`_resolve` rejects any path that escapes it (../, absolute paths, symlinks).
This is the file-isolation boundary; it lives here and nowhere else.
"""

from __future__ import annotations

from pathlib import Path

from .base import Tool


class _Scoped:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        target = (self.workspace / path).resolve()
        if not target.is_relative_to(self.workspace):
            raise ValueError(f"path '{path}' escapes the workspace")
        return target


class ReadFile(_Scoped, Tool):
    name = "read_file"
    description = "Read a UTF-8 text file from the workspace."
    input_schema = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Path relative to the workspace."}},
        "required": ["path"],
    }

    def run(self, path: str) -> str:
        target = self._resolve(path)
        if not target.exists():
            return f"Error: '{path}' does not exist"
        return target.read_text(encoding="utf-8")


class WriteFile(_Scoped, Tool):
    name = "write_file"
    description = "Write (create or overwrite) a UTF-8 text file in the workspace."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path relative to the workspace."},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    }

    def run(self, path: str, content: str) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {path}"


class ListFiles(_Scoped, Tool):
    name = "list_files"
    description = "List files in the workspace (recursively)."
    input_schema = {"type": "object", "properties": {}}

    def run(self) -> str:
        files = [
            str(p.relative_to(self.workspace))
            for p in sorted(self.workspace.rglob("*"))
            if p.is_file()
        ]
        return "\n".join(files) if files else "(workspace is empty)"
