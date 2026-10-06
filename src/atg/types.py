"""Public node and input-binding models.

Node shape follows Zhang et al. (2026), Atomic Task Graph, Definition 3:
a node is one tool invocation with inputs and outputs. Modeling standard
is Decision 0006 (Pydantic v2). Bindings are literals or ``$ref`` objects
per Decision 0007. Independent reimplementation; see docs/ATTRIBUTION.md
(``zhang2026atg``).
"""

from enum import Enum
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

_NODE_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_REF = re.compile(
    r"^(?P<node>[A-Za-z_][A-Za-z0-9_-]*)\.outputs\.(?P<field>[A-Za-z_][A-Za-z0-9_-]*)$"
)


class NodeStatus(str, Enum):
    pending = "pending"
    ready = "ready"
    running = "running"
    done = "done"
    failed = "failed"
    frozen = "frozen"


class Ref(BaseModel):
    """One ``$ref`` pointing at ``node_id.outputs.field``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    node_id: str
    field: str


def parse_ref(value: Any) -> Ref | None:
    """Return a ref, ``None`` for a literal, or raise ``ValueError`` if malformed."""

    if not isinstance(value, dict) or "$ref" not in value:
        return None
    if len(value) != 1:
        raise ValueError("$ref bindings must be an object with only the $ref key")
    raw = value["$ref"]
    if not isinstance(raw, str):
        raise ValueError("$ref must be a string")
    match = _REF.match(raw)
    if not match:
        raise ValueError("$ref must look like node_id.outputs.field")
    return Ref(node_id=match.group("node"), field=match.group("field"))


class TaskNode(BaseModel):
    """One ATG node. Frozen so status changes go through ``TaskGraph.transition``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    tool_name: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] | None = None
    declared_outputs: list[str] = Field(default_factory=list)
    status: NodeStatus = NodeStatus.pending
    parent_id: str | None = None
    refine: bool = True
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "parent_id", "tool_name")
    @classmethod
    def _identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _NODE_ID.match(value):
            raise ValueError(
                "identifiers must match ^[A-Za-z_][A-Za-z0-9_-]*$"
            )
        return value

    @field_validator("inputs")
    @classmethod
    def _inputs(cls, value: dict[str, Any]) -> dict[str, Any]:
        for item in value.values():
            parse_ref(item)
        return dict(value)

    @field_validator("declared_outputs")
    @classmethod
    def _declared_outputs(cls, value: list[str]) -> list[str]:
        for name in value:
            if not _NODE_ID.match(name):
                raise ValueError(f"bad output field {name!r}")
        if len(set(value)) != len(value):
            raise ValueError("duplicate declared output")
        return list(value)
