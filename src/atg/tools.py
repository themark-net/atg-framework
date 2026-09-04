"""Tool registry: OpenAI-style schema plus same-name callable.

Decision 0007. Implements the paper notion of an atomic tool ``f: I → O``
(Zhang et al. 2026, Def. 2–3 / §4.1) as an engineering contract. See
docs/ATTRIBUTION.md.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from atg.types import InputRef


class ToolSpec(BaseModel):
    """Registry entry: planning schema + execution flags."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    refine: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Name → (schema metadata + callable). Names are unique."""

    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._callables: dict[str, Callable[..., Any]] = {}

    def __contains__(self, name: str) -> bool:
        return name in self._specs

    def names(self) -> set[str]:
        return set(self._specs)

    def get(self, name: str) -> ToolSpec:
        try:
            return self._specs[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool {name!r}") from exc

    def register(
        self,
        spec: ToolSpec,
        fn: Callable[..., Any],
    ) -> ToolSpec:
        if spec.name in self._specs:
            raise ValueError(f"Duplicate tool name {spec.name!r}")
        self._specs[spec.name] = spec
        self._callables[spec.name] = fn
        return spec

    def callable_for(self, name: str) -> Callable[..., Any]:
        try:
            return self._callables[name]
        except KeyError as exc:
            raise KeyError(f"No callable bound for {name!r}") from exc

    def run(self, name: str, **kwargs: Any) -> Any:
        return self.callable_for(name)(**kwargs)

    def openai_tools(self) -> list[dict[str, Any]]:
        return [self._specs[n].openai_schema() for n in sorted(self._specs)]

    def may_refine(self, name: str) -> bool:
        if name not in self._specs:
            return True
        return self._specs[name].refine


def parse_input_value(value: Any) -> InputRef | Any:
    """Treat ``{\"$ref\": \"...\"}`` dicts as ``InputRef``."""
    if isinstance(value, InputRef):
        return value
    if isinstance(value, dict) and "$ref" in value:
        return InputRef.model_validate(value)
    return value


def resolve_inputs(
    inputs: dict[str, Any],
    outputs_by_node: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Bind literals as-is; resolve ``$ref`` against completed node outputs."""
    bound: dict[str, Any] = {}
    for key, raw in inputs.items():
        value = parse_input_value(raw)
        if isinstance(value, InputRef):
            node_id, field = value.parse()
            if node_id not in outputs_by_node:
                raise KeyError(f"$ref {value.ref!r} points at unknown node {node_id!r}")
            node_out = outputs_by_node[node_id]
            if field not in node_out:
                raise KeyError(
                    f"$ref {value.ref!r} missing output field {field!r} on {node_id!r}"
                )
            bound[key] = node_out[field]
        else:
            bound[key] = value
    return bound
