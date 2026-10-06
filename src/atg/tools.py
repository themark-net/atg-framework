"""Tool registry: OpenAI-style schema plus a same-name callable.

Zhang et al. (2026), Atomic Task Graph, Definition 2, treat a tool as an
atomic input-output unit. How that unit is registered is Decision 0007:
JSON schema for planning, callable for execution, ``refine=False`` to
force a node atomic. Independent reimplementation; see
docs/ATTRIBUTION.md (``zhang2026atg``).
"""

from collections.abc import Callable
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from atg.types import TaskNode

_TOOL_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


class ToolError(Exception):
    """Duplicate registration or unknown tool name."""


class ToolSchema(BaseModel):
    """Planner-facing tool description. The callable lives on the registry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str
    parameters: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    refine: bool = True

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        if not _TOOL_NAME.match(value):
            raise ValueError("tool name must match ^[A-Za-z_][A-Za-z0-9_-]*$")
        return value


class RegisteredTool:
    def __init__(self, spec: ToolSchema, fn: Callable[..., Any]) -> None:
        self.spec = spec
        self.fn = fn


class ToolRegistry:
    """Unique tool name → schema + callable."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def register(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
        description: str,
        parameters: dict[str, Any] | None = None,
        refine: bool = True,
    ) -> ToolSchema:
        tool_name = name or fn.__name__
        if tool_name in self._tools:
            raise ToolError(f"duplicate tool {tool_name}")
        spec = ToolSchema(
            name=tool_name,
            description=description,
            parameters=parameters
            if parameters is not None
            else {"type": "object", "properties": {}},
            refine=refine,
        )
        self._tools[tool_name] = RegisteredTool(spec=spec, fn=fn)
        return spec

    def get(self, name: str) -> RegisteredTool:
        try:
            return self._tools[name]
        except KeyError:
            raise ToolError(f"unknown tool {name}") from None

    def names(self) -> list[str]:
        return sorted(self._tools)

    def as_openai_tools(self) -> list[dict[str, Any]]:
        exported: list[dict[str, Any]] = []
        for name in self.names():
            spec = self._tools[name].spec
            exported.append(
                {
                    "type": "function",
                    "function": {
                        "name": spec.name,
                        "description": spec.description,
                        "parameters": spec.parameters,
                    },
                }
            )
        return exported


def is_atomic(node: TaskNode, registry: ToolRegistry | None = None) -> bool:
    """Compile stop rule from Decision 0007.

    Atomic when ``refine`` is false, or when ``tool_name`` is registered.
    A registered tool is executable, so the planner must not expand it.
    ``refine=False`` on the tool is stored for that same stop rule; pass
    the registry so registration can be seen.
    """

    if not node.refine:
        return True
    if registry is not None and node.tool_name and node.tool_name in registry:
        return True
    return False
