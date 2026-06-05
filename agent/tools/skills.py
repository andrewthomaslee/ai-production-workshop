"""The `load_skill` tool.

Skills are progressive disclosure: the system prompt only lists their names +
descriptions (cheap). When the agent decides a skill is relevant, it loads the
full instructions on demand with this tool. That keeps context small and makes
"a skill is just a markdown file" obvious.
"""

from __future__ import annotations

from .base import Tool
from ..skills import SkillLibrary


class LoadSkill(Tool):
    name = "load_skill"
    description = "Load the full instructions for a skill by name. Do this before acting on a matching task."
    input_schema = {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "The skill name from the catalog."}},
        "required": ["name"],
    }

    def __init__(self, skills: SkillLibrary):
        self.skills = skills

    def run(self, name: str) -> str:
        body = self.skills.body(name)
        if body is None:
            available = ", ".join(n for n, _ in self.skills.catalog()) or "(none)"
            return f"Error: no skill named '{name}'. Available: {available}"
        return body
