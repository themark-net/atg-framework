"""Public node, status, and binding models.

Pydantic v2 is the modeling standard (Decision 0006). Graph *topology* lives
in ``atg.graph`` (Decision 0005). Field lists may evolve in implementation PRs.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NodeStatus(str, Enum):
    """Lifecycle of a task node during plan / execute / repair."""

    pending = "pending"
    ready = "ready"
    running = "running"
    done = "done"
    failed = "failed"
    frozen = "frozen"


class InputRef(BaseModel):
    """Explicit binding to an upstream node output (Decision 0007 F4).

    Serialized form accepted in node inputs::

        {"$ref": "node_a.outputs.text"}
    """

    model_config = ConfigDict(populate_by_name=True)

    ref: str = Field(alias="$ref")

    @classmethod
    def from_path(cls, node_id: str, field: str) -> InputRef:
        return cls(ref=f"{node_id}.outputs.{field}")

    def parse(self) -> tuple[str, str]:
        """Return ``(node_id, output_field)``.

        Accepts ``node_id.outputs.field`` or the shorter ``node_id.field``.
        """
        parts = self.ref.split(".")
        if len(parts) >= 3 and parts[1] == "outputs":
            return parts[0], ".".join(parts[2:])
        if len(parts) == 2:
            return parts[0], parts[1]
        raise ValueError(f"Invalid $ref path: {self.ref!r}")


class TaskNode(BaseModel):
    """One tool invocation or abstract subtask (paper node ``v = (i, f, o)``)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    tool_name: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] | None = None
    status: NodeStatus = NodeStatus.pending
    parent_id: str | None = None
    refine: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_atomic(self, registered_tools: set[str] | None = None) -> bool:
        """Atomic if refine is forced off, or tool_name is a registered executable."""
        if self.refine is False:
            return True
        if registered_tools is None:
            return self.tool_name is not None
        return self.tool_name is not None and self.tool_name in registered_tools


class TaskSpec(BaseModel):
    """User-facing problem statement and desired external interface."""

    description: str
    outputs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
