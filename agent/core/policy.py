"""Role-based access control for tools.

The whole permission model in one place: a mapping from role -> the set of tools
that role may use. The `ToolRegistry` consults this both when *advertising* tools
to the model (a viewer never even sees `run_python`) and when *dispatching* a
call (defence in depth: the check runs again at execution time).

Roles are ordered by privilege; each inherits the tools of the ones below it.
For a real deployment you'd load this from config / an identity provider, but the
shape ("who may run what") stays exactly this.
"""

from __future__ import annotations

# What each role may do. Higher roles are supersets of lower ones.
_VIEWER = {"read_file", "list_files", "load_skill", "web_search", "web_fetch"}
_ANALYST = _VIEWER | {"write_file", "run_python", "install_packages", "remember",
                      "start_training", "training_status"}
# Deploying is privileged: an analyst can BUILD a site, only an admin can SHIP it.
_ADMIN = _ANALYST | {"deploy_site"}

ROLE_TOOLS: dict[str, set[str]] = {
    "viewer": _VIEWER,    # read-only: look around, recall, research the web
    "analyst": _ANALYST,  # + run code, write files, train models, remember
    "admin": _ADMIN,      # + deploy to production
}

ROLES = list(ROLE_TOOLS.keys())


class Policy:
    def __init__(self, role_tools: dict[str, set[str]] | None = None):
        self.role_tools = role_tools or ROLE_TOOLS

    def allows(self, role: str, tool_name: str) -> bool:
        return tool_name in self.role_tools.get(role, set())

    def allowed_tools(self, role: str) -> set[str]:
        return set(self.role_tools.get(role, set()))
