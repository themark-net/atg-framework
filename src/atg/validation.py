"""Acyclicity and interface checks.

Interface preservation follows Zhang et al. (2026), Atomic Task Graph,
§4.1: a replacement subgraph consumes the parent’s external inputs and
produces the parent’s declared outputs. Phase 1 checks ``$ref`` bindings
and declared sink outputs. Literal input values are not compared.
Acyclicity is Decision 0005. Independent reimplementation; see
docs/ATTRIBUTION.md (``zhang2026atg``).
"""

from atg.graph import TaskGraph
from atg.types import TaskNode, parse_ref


class InterfaceError(Exception):
    """A ``$ref`` or a parent/subgraph interface does not line up."""


def assert_valid(graph: TaskGraph) -> None:
    """Closed graph: acyclic, and every ``$ref`` points at an ancestor field."""

    graph.topological_order()
    assert_refs(graph)


def assert_refs(graph: TaskGraph, *, allow_external: bool = False) -> None:
    for node_id in graph.node_ids():
        node = graph.get(node_id)
        for key, value in node.inputs.items():
            ref = parse_ref(value)
            if ref is None:
                continue
            if ref.node_id not in graph:
                if allow_external:
                    continue
                raise InterfaceError(
                    f"{node.id}.{key} references missing node {ref.node_id}"
                )
            if ref.node_id not in graph.ancestors(node.id):
                raise InterfaceError(
                    f"{node.id}.{key} $ref {ref.node_id} is not an ancestor"
                )
            _require_field(graph.get(ref.node_id), ref.field, owner=node.id, key=key)


def assert_interface_preserved(parent: TaskNode, subgraph: TaskGraph) -> None:
    """The subgraph may replace ``parent`` without changing external I/O."""

    if len(subgraph) == 0:
        raise InterfaceError("replacement subgraph is empty")
    subgraph.topological_order()
    assert_refs(subgraph, allow_external=True)

    parent_refs: set[tuple[str, str]] = set()
    for value in parent.inputs.values():
        ref = parse_ref(value)
        if ref is not None:
            parent_refs.add((ref.node_id, ref.field))

    used: set[tuple[str, str]] = set()
    for node_id in subgraph.node_ids():
        node = subgraph.get(node_id)
        for value in node.inputs.values():
            ref = parse_ref(value)
            if ref is None or ref.node_id in subgraph:
                continue
            pair = (ref.node_id, ref.field)
            if pair not in parent_refs:
                raise InterfaceError(
                    f"{node.id} external ref {ref.node_id}.outputs.{ref.field} "
                    "is not on the parent interface"
                )
            used.add(pair)

    missing_inputs = parent_refs - used
    if missing_inputs:
        listed = ", ".join(
            f"{node_id}.outputs.{field}" for node_id, field in sorted(missing_inputs)
        )
        raise InterfaceError(f"subgraph does not consume parent inputs: {listed}")

    if not parent.declared_outputs:
        return
    produced: set[str] = set()
    for node_id in subgraph.node_ids():
        if subgraph.successors(node_id):
            continue
        produced.update(subgraph.get(node_id).declared_outputs)
    missing_outputs = [name for name in parent.declared_outputs if name not in produced]
    if missing_outputs:
        raise InterfaceError(f"sinks missing declared outputs {missing_outputs}")


def _require_field(node: TaskNode, field: str, *, owner: str, key: str) -> None:
    if node.declared_outputs and field not in node.declared_outputs:
        raise InterfaceError(
            f"{owner}.{key} needs {node.id}.outputs.{field}, which is not declared"
        )
    if node.outputs is not None and field not in node.outputs:
        raise InterfaceError(
            f"{owner}.{key} needs {node.id}.outputs.{field}, which was not produced"
        )
