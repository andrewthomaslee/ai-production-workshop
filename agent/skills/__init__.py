"""Skill loading.

A skill is a folder under agent/skills/<name>/ containing a SKILL.md file with
a tiny YAML-ish front matter:

    ---
    name: data-analysis
    description: Explore and analyze a dataset with pandas.
    ---
    <full instructions the agent loads on demand>

The catalog (name + description) is cheap and always shown. The body is loaded
only when the agent asks for it. No code lives in a skill; it's pure data, so
non-coders can author one.
"""

from __future__ import annotations

from pathlib import Path


def _parse(md: str) -> tuple[dict, str]:
    """Split optional `--- front matter ---` from the body. Tiny on purpose."""
    meta: dict[str, str] = {}
    body = md
    if md.startswith("---"):
        _, fm, body = md.split("---", 2)
        for line in fm.strip().splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip()
    return meta, body.strip()


class SkillLibrary:
    def __init__(self, root: Path):
        self.root = root
        self._skills: dict[str, tuple[str, str]] = {}  # name -> (description, body)
        self._load()

    def _load(self) -> None:
        for skill_md in sorted(self.root.glob("*/SKILL.md")):
            meta, body = _parse(skill_md.read_text(encoding="utf-8"))
            name = meta.get("name", skill_md.parent.name)
            description = meta.get("description", "(no description)")
            self._skills[name] = (description, body)

    def catalog(self) -> list[tuple[str, str]]:
        return [(name, desc) for name, (desc, _) in self._skills.items()]

    def body(self, name: str) -> str | None:
        entry = self._skills.get(name)
        return entry[1] if entry else None

    def reload(self) -> None:
        self._skills.clear()
        self._load()

    def save(self, name: str, description: str, body: str) -> None:
        """Create or update a skill from the UI (the no-code authoring path).

        Writes skills/<name>/SKILL.md with front matter, then reloads so the new
        skill is immediately visible in the catalog and loadable by the agent.
        """
        slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in name.lower()).strip("-") or "skill"
        skill_dir = self.root / slug
        skill_dir.mkdir(parents=True, exist_ok=True)
        md = f"---\nname: {name}\ndescription: {description}\n---\n\n{body.strip()}\n"
        (skill_dir / "SKILL.md").write_text(md, encoding="utf-8")
        self.reload()


__all__ = ["SkillLibrary"]
