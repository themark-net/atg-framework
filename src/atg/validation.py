"""DAG integrity and basic interface checks.

Architecture §5.5. Phase 1 covers acyclicity plus $ref targets that exist
on the graph. Richer interface-preservation checks land with the planner.
"""

from __future__ import annotations

from atg.graph import TaskGraph
from atg.tools import parse_input_value
from atg.types import InputRef


class ValidationError(ValueError):
    """Graph or interface invariant failed."""


def validate_acyclic(graph: TaskGraph) -> None:
    if graph.has_cycle():
        raise ValidationError("Graph contains a cycle")


def validate_refs(graph: TaskGraph) -> None:
    ids = set(graph.node_ids())
    for node in graph.nodes():
        for key, raw in node.inputs.items():
            value = parse_input_value(raw)
            if not isinstance(value, InputRef):
                continue
            src_id, _field = value.parse()
            if src_id not in ids:
                raise ValidationError(
                    f"Node {node.id!r} input {key!r} $ref targets unknown node {src_id!r}"
                )
            if src_id == node.id:
                raise ValidationError(
                    f"Node {node.id!r} input {key!r} $ref points at itself"
                )


def validate_graph(graph: TaskGraph) -> None:
    validate_acyclic(graph)
    validate_refs(graph)
