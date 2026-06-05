"""Per-user sessions: how one deployment safely serves many users.

A `Session` owns everything that must NOT be shared between users:
  - the conversation `history` (inside its own `Agent`)
  - a per-user `Memory` file
  - a per-user `workspace/` (and sandbox package dir, derived from it)
  - a `ToolRegistry` bound to that user's role (so permissions are per-user)

Shared, app-level things (the skill library, the model client, the policy, the
audit log) are passed in. A `SessionStore` hands out one `Session` per user and
caches it. This is the difference between a demo and a multi-tenant system: there
is no global mutable state that one user can use to see another user's data.

For the workshop the store is in-memory. The comments mark exactly where Redis /
a database would slot in for horizontal scaling; the boundary is already clean.
"""

from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from .audit import AuditLog
from .context import Context
from .loop import Agent
from .policy import Policy
from ..memory.store import Memory
from ..sandbox.runner import get_runner
from ..skills import SkillLibrary
from ..tools import ToolRegistry
from ..tools.fs import ListFiles, ReadFile, WriteFile
from ..tools.install import InstallPackages
from ..tools.memory import Remember
from ..tools.python import RunPython
from ..tools.skills import LoadSkill
from ..tools.web import WebFetch, WebSearch
from ..tools.deploy import DeploySite
from ..tools.training import StartTraining, TrainingStatus


def build_tools(workspace: Path, runner, memory: Memory, skills: SkillLibrary) -> list:
    """The full tool set, constructed for one user. Adding a capability = adding
    one line here (and a policy entry in policy.py)."""
    return [
        # Files (scoped to this user's workspace)
        ReadFile(workspace), WriteFile(workspace), ListFiles(workspace),
        # Code execution (this user's sandbox)
        RunPython(runner), InstallPackages(runner),
        # Memory & skills
        Remember(memory), LoadSkill(skills),
        # Project tools (P2 marketing research, P3 ML training, P4 website ship)
        WebSearch(), WebFetch(),
        StartTraining(workspace), TrainingStatus(workspace),
        DeploySite(workspace),
    ]


class Session:
    def __init__(
        self,
        user_id: str,
        role: str,
        model: str,
        sandbox_kind: str,
        *,
        root: Path,
        skills: SkillLibrary,
        client: OpenAI,
        policy: Policy | None,
        audit: AuditLog | None,
    ):
        self.user_id = user_id
        self.role = role
        self.model = model
        self.sandbox_kind = sandbox_kind

        base = root / "data" / user_id
        self.workspace = base / "workspace"
        self.memory = Memory(base / "memory.md")
        self.runner = get_runner(sandbox_kind, self.workspace)

        tools = build_tools(self.workspace, self.runner, self.memory, skills)
        self.registry = ToolRegistry(tools, policy=policy, audit=audit, role=role, user_id=user_id)
        self.context = Context(skills, self.memory)
        self.agent = Agent(client, model, self.context, self.registry)

    # Role and model can change between requests (e.g. the UI lets you switch
    # role to demo RBAC). The registry reads role live, so this is all it takes.
    def set_role(self, role: str) -> None:
        self.role = role
        self.registry.role = role

    def set_model(self, model: str) -> None:
        self.model = model
        self.agent.model = model

    def reset(self) -> None:
        self.agent.history = []


class SessionStore:
    """One Session per user_id, cached. Swap this dict for Redis to scale out."""

    def __init__(self, *, root: Path, skills: SkillLibrary, client: OpenAI,
                 policy: Policy | None, audit: AuditLog | None):
        self.root = root
        self.skills = skills
        self.client = client
        self.policy = policy
        self.audit = audit
        self._sessions: dict[str, Session] = {}

    def get(self, user_id: str, role: str, model: str, sandbox_kind: str) -> Session:
        session = self._sessions.get(user_id)
        if session is None:
            session = Session(
                user_id, role, model, sandbox_kind,
                root=self.root, skills=self.skills, client=self.client,
                policy=self.policy, audit=self.audit,
            )
            self._sessions[user_id] = session
        else:
            session.set_role(role)
            session.set_model(model)
        return session

    def users(self) -> list[str]:
        return list(self._sessions)
