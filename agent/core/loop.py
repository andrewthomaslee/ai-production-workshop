"""The agentic loop.

This is the whole "agent". An agent is a `while` loop around an LLM call:
  1. ask the model what to do (given tools, skills, memory)
  2. if it wants to use a tool, run the tool and feed the result back
  3. repeat until the model has nothing left to do but answer

Everything else in this codebase is just *what tools exist* and *what goes
into the system prompt*. Read this file first.

This implementation uses the OpenAI Chat Completions API. The only
OpenAI-specific details live here and in tools/registry.py (tool schema
format); the rest of the framework is provider-agnostic.
"""

from __future__ import annotations

import json
from typing import Callable

from openai import OpenAI

from .context import Context
from ..tools import ToolRegistry


class Agent:
    def __init__(
        self,
        client: OpenAI,
        model: str,
        context: Context,
        tools: ToolRegistry,
        on_event: Callable[[str, dict], None] | None = None,
        max_turns: int = 50,
    ):
        self.client = client
        self.model = model
        self.context = context
        self.tools = tools
        self.history: list[dict] = []
        self.max_turns = max_turns
        # on_event lets the CLI (or a UI) watch the loop: "thinking", "tool", "result".
        self.on_event = on_event or (lambda kind, data: None)

    def run(self, user_message: str, on_event: Callable[[str, dict], None] | None = None) -> str:
        """Run the loop until the model produces a final text answer.

        `on_event` (optional) overrides the instance callback for this call;
        the server passes a per-request streamer so each WebSocket connection
        sees only its own steps.
        """
        emit = on_event or self.on_event
        self.history.append({"role": "user", "content": user_message})

        for _ in range(self.max_turns):
            response = self.client.chat.completions.create(
                model=self.model,
                # The system prompt (base + skills catalog + memory) is rebuilt
                # each turn and prepended; self.history is the running transcript.
                messages=[{"role": "system", "content": self.context.build()}] + self.history,
                tools=self.tools.schemas(),
            )
            message = response.choices[0].message
            self.history.append(message)  # keep the assistant turn in the transcript

            # Surface any text the model produced this turn.
            if message.content:
                emit("thinking", {"text": message.content})

            # No tool requested -> the model is done. Return its answer.
            if not message.tool_calls:
                return message.content or ""

            # Otherwise, run every requested tool and feed the results back.
            for call in message.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                emit("tool", {"name": call.function.name, "input": args})
                output = self.tools.dispatch(call.function.name, args)
                emit("result", {"name": call.function.name, "output": output})
                self.history.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": output,
                })

        return "(stopped: hit max turns)"
