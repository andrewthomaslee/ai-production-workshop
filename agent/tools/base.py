"""The tool interface.

A tool is the agent's only way to affect the world. Every tool is the same
three things:
  - name           : what the model calls it
  - description     : when/how to use it (the model reads this)
  - input_schema    : a JSON Schema for the arguments
  - run(**kwargs)   : do the thing, return a string the model will read

Adding a capability = writing one subclass. Nothing else changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Tool(ABC):
    name: str
    description: str
    input_schema: dict

    @abstractmethod
    def run(self, **kwargs) -> str:
        ...
