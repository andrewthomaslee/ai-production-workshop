"""Collects tools and exposes them to the loop.

Three jobs:
  - schemas()  -> the tool list in OpenAI's function-calling format, FILTERED to
                  what the caller's role may use (a viewer never sees run_python)
  - dispatch() -> look up a tool by name and run it, enforcing the policy again
                  (defence in depth) and writing an audit record
  - errors are turned into readable strings the model can recover from

Permissions and auditing are optional: with no policy/audit (the CLI's default)
this behaves like a plain registry that allows everything. The server wires in a
Policy and an AuditLog so the same registry becomes multi-tenant and governed.
The OpenAI-specific schema shape lives only in schemas().
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Tool

if TYPE_CHECKING:  # avoid a circular import; these are only type hints here
    from ..core.audit import AuditLog
    from ..core.policy import Policy


class ToolRegistry:
    def __init__(
        self,
        tools: list[Tool],
        policy: Policy | None = None,
        audit: AuditLog | None = None,
        role: str = "admin",
        user_id: str = "local",
    ):
        self.tools = {t.name: t for t in tools}
        self.policy = policy
        self.audit = audit
        self.role = role
        self.user_id = user_id

    def _visible(self, name: str) -> bool:
        return self.policy is None or self.policy.allows(self.role, name)

    def schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in self.tools.values()
            if self._visible(t.name)
        ]

    def dispatch(self, name: str, tool_input: dict) -> str:
        tool = self.tools.get(name)
        if tool is None:
            return self._finish(name, tool_input, False, f"Error: unknown tool '{name}'")

        # Defence in depth: check the policy at execution time, not just at
        # advertise time. A model could hallucinate a tool name it shouldn't have.
        if not self._visible(name):
            msg = f"Error: permission denied; role '{self.role}' may not use '{name}'."
            return self._finish(name, tool_input, False, msg)

        try:
            result = tool.run(**tool_input)
        except Exception as exc:  # noqa: BLE001 (surface the error to the model)
            result = f"Error running {name}: {exc}"
        return self._finish(name, tool_input, True, result)

    def _finish(self, name: str, tool_input: dict, allowed: bool, result: str) -> str:
        if self.audit is not None:
            self.audit.record(
                user_id=self.user_id, role=self.role, tool=name,
                tool_input=tool_input, allowed=allowed, result=result,
            )
        return result
